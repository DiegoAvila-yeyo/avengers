# Prompt #18 — Hulk Anti-Alucinación: Validador de Referencias y Endpoints

**Fase**: 4 — Sistema de Calidad
**Agente objetivo**: Hulk
**Archivo(s) a crear**:
- `tools/hallucination_detector.py` — Detector de alucinaciones de código
**Dependencias previas**: Prompt #17 (HulkAgent, GuardrailReport), Prompt #09 (BlueprintV1)
**Checkpoint humano**: No

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en análisis de calidad de código
generado por LLMs, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → sección "Higiene de Contexto y Prevención de Alucinaciones".
3. Lee `core/blueprint_schema.py` → `BlueprintV1`, `ApiEndpoint`, `DataModel`.
4. Lee `pyproject.toml` → dependencias declaradas (fuente de verdad de libs permitidas).
5. Lee `agents/hulk.py` → `GuardrailViolation`, `ViolationType`, `HulkAgent.scan_file`.

---

### TAREA: Crear el detector de alucinaciones

#### ARCHIVO: `tools/hallucination_detector.py`

```python
class HallucinationDetector:
    """
    Detecta alucinaciones comunes en código generado por LLMs:
    1. Imports de librerías no declaradas en pyproject.toml.
    2. Llamadas a endpoints que no existen en el Blueprint.
    3. Referencias a modelos de datos que no están en el Blueprint.
    4. Variables de entorno accedidas directamente (no via Settings).
    """

    def __init__(
        self,
        blueprint: BlueprintV1,
        allowed_packages: set[str],    # Extraídos de pyproject.toml
        file_tools: FileTools,
    ): ...

    def check_imports(self, source_code: str, file_path: str) -> list[GuardrailViolation]:
        """
        Parsea los imports del código con ast.parse().
        Por cada `import X` o `from X import Y`:
        - Extrae el paquete raíz (e.g., 'httpx' de 'from httpx import AsyncClient').
        - Si no está en allowed_packages NI es stdlib → GuardrailViolation severity=error.
        - Mensaje: "Import alucinado: '{package}' no está en pyproject.toml"
        """

    def check_endpoints(self, source_code: str, file_path: str) -> list[GuardrailViolation]:
        """
        Busca strings que parezcan rutas de API (regex: r'["\'](/\w+)+["\']').
        Por cada ruta encontrada:
        - Verificar que exista en blueprint.api_endpoints.
        - Si no existe → GuardrailViolation severity=warning.
        - Mensaje: "Endpoint '{path}' no declarado en Blueprint"
        """

    def check_env_access(self, source_code: str, file_path: str) -> list[GuardrailViolation]:
        """
        Detecta acceso directo a variables de entorno:
        Patrones: os.environ, os.getenv, dotenv.load_dotenv en código no-settings.
        → GuardrailViolation severity=error.
        Excepción: archivos en core/settings.py y tests/.
        """

    def check_data_models(self, source_code: str, file_path: str) -> list[GuardrailViolation]:
        """
        Extrae nombres de clases definidas (ast.ClassDef).
        Si un nombre no está en blueprint.data_models ni en las interfaces estándar
        (BaseModel, Exception, Protocol, Enum, etc.) → GuardrailViolation severity=warning.
        """

    async def scan_all(self, file_paths: list[str]) -> list[GuardrailViolation]:
        """
        Ejecuta todos los checks sobre cada archivo.
        Lee contenido con file_tools.read_file(). [ROOT JAIL activo]
        """
```

**Restricciones**:
- Usar `ast.parse()` para análisis de imports y clases — no regex para Python syntax.
- Regex solo para patrones de strings (rutas de endpoints) y env access.
- `allowed_packages` se genera parseando `pyproject.toml` — no hardcodear nombres.
- **Este archivo NO debe superar 180 líneas.**

---

### INTEGRACIÓN CON HULK

Añadir en `agents/hulk.py` (Prompt #17):
```python
# En HulkAgent.scan_file(), añadir:
hallucination_violations = await self.hallucination_detector.scan_all([file_path])
violations.extend(hallucination_violations)
```

---

### TESTS REQUERIDOS: `tests/tools/test_hallucination_detector.py`

```python
# Test 1: detecta import de librería no en pyproject.toml
def test_detects_unknown_import(): ...

# Test 2: permite imports de stdlib (os, sys, pathlib...)
def test_allows_stdlib_imports(): ...

# Test 3: detecta endpoint hardcodeado no en Blueprint
def test_detects_undeclared_endpoint(): ...

# Test 4: detecta os.environ directo
def test_detects_direct_env_access(): ...

# Test 5: permite os.environ en core/settings.py
def test_allows_env_access_in_settings_file(): ...

# Test 6: detecta clase de modelo no declarada en Blueprint
def test_detects_undeclared_data_model(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `tools/hallucination_detector.py` < 180 líneas
- [ ] `ast.parse()` para imports y class definitions
- [ ] Regex solo para endpoint paths y env patterns
- [ ] `allowed_packages` desde `pyproject.toml` (no hardcodeado)
- [ ] Integrado en `HulkAgent.scan_file()`
- [ ] 6 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | `file_tools.read_file()` para leer archivos a escanear |
| **Hulk** | El detector se autoescanea — debe pasar sus propios checks |
| **Widow** | Los 4 check methods son independientes — ninguno se duplica |
