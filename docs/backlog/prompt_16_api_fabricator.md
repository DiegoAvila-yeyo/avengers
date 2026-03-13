# Prompt #16 — API-Fabricator: Protocolo de Invocación y Generación de Conectores

**Fase**: 3 — La Fábrica
**Agente objetivo**: API-Fabricator
**Archivo(s) a crear**:
- `agents/api_fabricator.py` — Agente lector de APIs y generador de conectores
**Dependencias previas**: Prompt #11 (file_tools), Prompt #12 (IronCoderAgent — invoca este agente)
**Checkpoint humano**: No

### 🔌 Protocolo de Invocación (v0.3.0)
Este agente existe ESPECÍFICAMENTE para ser invocado por Iron-Coder cuando detecta
un `ApiEndpoint` con `known_api=False` en el Blueprint. No actúa de forma autónoma.
El flujo de invocación es:

```
Iron-Coder detecta known_api=False
        ↓
IronCoderAgent._invoke_api_fabricator(api_names, mission)
        ↓
ApiFabricatorAgent.generate_connector(api_name, docs_source)
        ↓
tools/connectors/{api_name}_connector.py  ← conector generado
        ↓
Iron-Coder continúa la generación del módulo
```

### 🔒 Cláusula ROOT JAIL (v0.3.0) — OBLIGATORIA
**Los conectores generados DEBEN escribirse SOLO en `tools/connectors/` dentro del
project_root, usando `file_tools.write_file()`. Lanzar `RootJailViolationError` ante
cualquier intento de escribir en rutas externas.**

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en integración de APIs y generación
de clientes HTTP, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolos Hulk y Widow.
2. Lee `ARCHITECTURE.md` → rol de API-Fabricator en el Bucle Infinito.
3. Lee `core/blueprint_schema.py` → `ApiEndpoint`, `known_api`.
4. Lee `tools/file_tools.py` → `write_file`, `read_file`, `resolve_safe_path`.
5. Lee `core/exceptions.py` → `AgentExecutionError`, `RootJailViolationError`.

---

### TAREA: Implementar el agente API-Fabricator

#### ARCHIVO: `agents/api_fabricator.py`

```python
class ApiFabricatorAgent:
    """
    Lee documentación de APIs (OpenAPI/Swagger, README de GitHub, docs HTML)
    y genera conectores Python async usables por los demás agentes.

    Invocación: siempre desde IronCoderAgent, nunca directamente.
    Output: tools/connectors/{api_name}_connector.py
    """

    CONNECTOR_SYSTEM_PROMPT: ClassVar[str] = """
    Eres un experto en integración de APIs. Genera un conector Python async.
    Reglas absolutas:
    - Usa httpx.AsyncClient como cliente HTTP — nunca requests (síncrono).
    - Manejo de errores: captura httpx.HTTPStatusError, loggea y relanza.
    - Autenticación: parametrizable via constructor (no hardcodear keys).
    - Un método por endpoint documentado. Nombres en snake_case.
    - Type hints completos en todas las firmas (Pydantic v2 para request/response).
    - El conector es stateless: sin atributos mutables de instancia.
    - LÍMITE: 250 líneas máximo (deja margen al Protocolo Hulk).
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        file_tools: FileTools,
        project_root: Path,
    ): ...

    async def generate_connector(
        self,
        api_name: str,               # snake_case — e.g. "stripe_payments"
        docs_source: str,            # URL de OpenAPI spec, GitHub README URL, o texto raw
        mission: Mission,
    ) -> Path:
        """
        1. Obtener documentación: si docs_source es URL → httpx.get() y extraer texto.
           Si docs_source es texto raw → usar directamente.
        2. Llamar LLM con CONNECTOR_SYSTEM_PROMPT + docs_text.
        3. Parsear código generado.
        4. Verificar: si el conector supera 250L → solicitar división al LLM.
        5. Guardar en tools/connectors/{api_name}_connector.py via file_tools. [ROOT JAIL]
        6. Registrar StateLogEntry en la misión.
        7. Retornar la ruta del conector creado.

        Errores:
        - Si URL inaccesible → lanzar AgentExecutionError (Fury activará retry).
        - Si LLM genera código con imports no en pyproject.toml → rechazar y relanzar.
        """

    async def validate_connector(self, connector_path: str) -> bool:
        """
        Validación básica del conector generado:
        1. Sintaxis Python válida (compile(source, ...)).
        2. Ningún import de librerías no declaradas en pyproject.toml.
        3. Al menos un método async definido.
        4. Archivo dentro del ROOT JAIL (resolve_safe_path check).
        Retorna True si válido, lanza AgentExecutionError si no.
        """
```

**Restricciones**:
- `generate_connector` usa `httpx.AsyncClient` para fetch de docs — no `requests`.
- El output SIEMPRE va a `tools/connectors/{api_name}_connector.py`.
- **Este archivo NO debe superar 180 líneas.**

---

### TESTS REQUERIDOS: `tests/agents/test_api_fabricator.py`

```python
# Test 1: generate_connector con OpenAPI spec URL → conector generado en tools/connectors/
async def test_generate_connector_from_url(): ...

# Test 2: conector > 250L → LLM solicitado a dividir antes de guardar
async def test_oversized_connector_triggers_split_request(): ...

# Test 3: URL inaccesible → AgentExecutionError (Fury maneja retry)
async def test_inaccessible_url_raises_agent_execution_error(): ...

# Test 4: conector escrito SOLO en tools/connectors/ (ROOT JAIL)
async def test_connector_written_inside_root_jail(): ...

# Test 5: validate_connector rechaza imports desconocidos
async def test_validate_rejects_unknown_imports(): ...

# Test 6: validate_connector rechaza archivo sin métodos async
async def test_validate_rejects_no_async_methods(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `agents/api_fabricator.py` < 180 líneas
- [ ] Escritura SOLO en `tools/connectors/` via `file_tools`
- [ ] `validate_connector` implementado con 4 checks
- [ ] `AgentExecutionError` en caso de URL inaccesible
- [ ] Conectores con type hints completos y httpx async
- [ ] 6 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | Escritura SOLO en `tools/connectors/` via `file_tools` |
| **Invocación** | Solo desde `IronCoderAgent._invoke_api_fabricator()` |
| **Hulk** | Conector > 250L → pedir split al LLM antes de guardar |
| **Widow** | Cero código muerto en el conector generado |
