# Prompt #12 — Iron-Coder: Generador de Backend FastAPI + Invocación API-Fabricator

**Fase**: 3 — La Fábrica
**Agente objetivo**: Iron-Coder
**Archivo(s) a crear**:
- `agents/iron_coder.py` — Agente generador de módulos FastAPI
**Dependencias previas**: Prompt #11 (file_tools, shell_tools), Prompt #10 (BlueprintV1, MissionMap)
**Checkpoint humano**: No

### 🔒 Cláusula ROOT JAIL (v0.3.0) — OBLIGATORIA
**Toda operación de escritura/lectura de archivos realizada por Iron-Coder DEBE
usar `tools.file_tools.write_file()` y `read_file()` — nunca `open()` directo ni `pathlib`
sin pasar por `resolve_safe_path`. El sistema debe lanzar `RootJailViolationError`
si se detecta acceso fuera del directorio raíz del proyecto.**

### 🔌 Enmienda: Invocación API-Fabricator (v0.3.0)
**Si Iron-Coder encuentra en el Blueprint un `ApiEndpoint` con `known_api=False`,
DEBE pausar la generación del módulo afectado e invocar el `ApiFabricatorAgent`
para generar el conector antes de continuar. No puede "improvisar" el conector.**

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en FastAPI y generación de código
por LLM, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolos Hulk y Widow.
2. Lee `ARCHITECTURE.md` → rol de Iron-Coder, ciclo de construcción.
3. Lee `core/blueprint_schema.py` → `BlueprintV1`, `MissionMap`, `ApiEndpoint.known_api`.
4. Lee `tools/file_tools.py` → `write_file`, `read_file`, `resolve_safe_path`.
5. Lee `core/exceptions.py` → `RootJailViolationError`, `AgentExecutionError`.
6. Lee `missions/{mission_id}/MAP.yaml` → qué archivos debe crear en esta misión.

---

### TAREA: Implementar el agente Iron-Coder

#### ARCHIVO: `agents/iron_coder.py`

```python
class IronCoderAgent:
    """
    Genera módulos FastAPI a partir del BlueprintV1.
    Opera módulo a módulo (JIT context): un módulo = un LLM call.
    """

    SYSTEM_PROMPT: ClassVar[str] = """
    Eres un Senior Backend Developer. Tu output es SIEMPRE código Python 3.12+ válido.
    Reglas absolutas:
    - FastAPI para endpoints. Pydantic v2 para schemas. Motor async para MongoDB.
    - Ningún archivo generado puede superar 300 líneas (Protocolo Hulk).
      Si el módulo requiere más → divide en sub-módulos y documenta la división.
    - Snake_case para funciones y variables. PascalCase para clases.
    - Manejo de errores: HTTPException con códigos correctos (400/404/422/500).
    - Incluye docstrings en todas las funciones públicas.
    - NO uses librerías fuera de pyproject.toml. Si necesitas una nueva → documenta y DETENTE.
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        file_tools: FileTools,
        api_fabricator: "ApiFabricatorAgent",  # Inyectado para invocación JIT
        project_root: Path,
    ): ...

    async def run(self, mission: Mission) -> Mission:
        """
        Itera sobre blueprint.modules y genera cada módulo en orden de dependencias.
        Para cada módulo:
        1. Verificar unknown APIs con `_check_unknown_apis(module, blueprint)`.
        2. Si hay unknown APIs → llamar `await self._invoke_api_fabricator(apis, mission)`.
        3. Generar el módulo con el LLM usando contexto JIT (solo el módulo actual).
        4. Guardar con `file_tools.write_file()` — [ROOT JAIL activo].
        5. Actualizar FileEntry en MAP.yaml (status="created", line_count=N).
        6. Registrar StateLogEntry en la misión.
        Retorna la misión actualizada.
        """

    async def _check_unknown_apis(
        self, module: "ModuleSpec", blueprint: BlueprintV1
    ) -> list[str]:
        """
        Retorna los nombres de APIs desconocidas que usa este módulo.
        Busca en blueprint.api_endpoints donde endpoint.module == module.module_name
        y endpoint.known_api == False.
        """

    async def _invoke_api_fabricator(
        self, api_names: list[str], mission: Mission
    ) -> list[Path]:
        """
        [API-FABRICATOR INVOCATION]
        Invoca ApiFabricatorAgent.generate_connector(api_name) para cada API desconocida.
        Los conectores se guardan en tools/connectors/{api_name}_connector.py.
        Actualiza MAP.yaml con los nuevos FileEntry.
        Si ApiFabricatorAgent falla → lanzar AgentExecutionError (Fury manejará el retry).
        NO improvisa el conector. DETENTE y delega.
        """

    async def _update_map(
        self, mission: Mission, file_path: str, line_count: int
    ) -> None:
        """
        Lee MAP.yaml, actualiza el FileEntry correspondiente
        (status="created", line_count=line_count), escribe MAP.yaml de vuelta.
        Usa file_tools — ROOT JAIL activo.
        """
```

**Restricciones**:
- Iron-Coder NUNCA usa `open()`, `Path.write_text()` o `os` directamente.
  Todo I/O pasa por `file_tools.write_file()` / `file_tools.read_file()`.
- El prompt al LLM incluye **solo** el `ModuleSpec` actual + las interfaces de sus dependencias.
  No inyectar el Blueprint completo — principio JIT.
- **Este archivo NO debe superar 200 líneas.** Si crece, extraer `_update_map` a `tools/map_tools.py`.

---

### TESTS REQUERIDOS: `tests/agents/test_iron_coder.py`

```python
# Test 1: run() itera sobre todos los módulos del Blueprint
async def test_run_generates_all_modules(): ...

# Test 2: módulo con known_api=False → _invoke_api_fabricator llamado
async def test_unknown_api_triggers_fabricator_invocation(): ...

# Test 3: si ApiFabricatorAgent falla → AgentExecutionError (no improvisar)
async def test_fabricator_failure_raises_agent_execution_error(): ...

# Test 4: todos los writes usan file_tools (no open() directo) — mock verify
async def test_all_writes_use_file_tools(): ...

# Test 5: MAP.yaml actualizado con status="created" tras generar módulo
async def test_map_updated_after_module_creation(): ...

# Test 6: RootJailViolationError propagado si file_tools la lanza
async def test_root_jail_violation_propagates(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `agents/iron_coder.py` < 200 líneas
- [ ] TODO I/O a través de `file_tools` — cero `open()` directo
- [ ] `_invoke_api_fabricator` implementado y testeado
- [ ] MAP.yaml actualizado tras cada módulo creado
- [ ] JIT context: LLM recibe solo el módulo actual
- [ ] 6 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | Todo I/O via `file_tools` — violación = `RootJailViolationError` |
| **API-Fabricator** | `known_api=False` → delegar, nunca improvisar |
| **Hulk** (> 300L) | Dividir módulo antes de escribirlo |
| **Widow** | Cero código muerto |
