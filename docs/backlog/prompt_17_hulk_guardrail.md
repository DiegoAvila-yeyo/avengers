# Prompt #17 — Hulk Guardrail: Validador de 300 Líneas e Imports

**Fase**: 4 — Sistema de Calidad
**Agente objetivo**: Hulk
**Archivo(s) a crear**:
- `agents/hulk.py` — Agente validador: límite de líneas + imports no usados
**Dependencias previas**: Prompt #11 (file_tools, count_lines), Prompt #12 (MAP.yaml)
**Checkpoint humano**: No

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en análisis estático de código
y guardianes de calidad, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → Protocolo Hulk (el que implementas aquí).
2. Lee `ARCHITECTURE.md` → rol de Hulk como Guardrail del sistema.
3. Lee `tools/file_tools.py` → `count_lines`, `list_files`, `read_file`.
4. Lee `tools/shell_tools.py` → `run_command` (para ruff).
5. Lee `core/constants.py` → `MAX_FILE_LINES = 300`.

---

### TAREA: Implementar el agente Hulk como validador estático

#### ARCHIVO: `agents/hulk.py`

```python
class ViolationType(str, Enum):
    LINE_LIMIT = "line_limit"          # Archivo supera MAX_FILE_LINES
    UNUSED_IMPORT = "unused_import"    # Import declarado sin usar
    DEAD_CODE = "dead_code"            # Función/clase definida, nunca referenciada
    FORBIDDEN_PATTERN = "forbidden"    # open(), os.system(), subprocess sin jail


class GuardrailViolation(BaseModel):
    file_path: str
    violation_type: ViolationType
    line_number: int | None
    detail: str
    severity: str   # "error" | "warning"


class GuardrailReport(BaseModel):
    mission_id: str
    scanned_files: int
    violations: list[GuardrailViolation]
    passed: bool                        # True solo si len(violations con severity="error") == 0
    generated_at: datetime


class HulkAgent:
    """
    Guardrail del sistema. Escanea el código generado por Iron-Coder y Vision-UI.
    Si encuentra violaciones 'error' → lanza HulkViolationError (bloquea avance).
    Si solo hay 'warning' → reporta pero no bloquea.
    """

    FORBIDDEN_PATTERNS: ClassVar[list[str]] = [
        r"\bopen\s*\(",           # open() sin file_tools
        r"\bos\.system\s*\(",     # shell directo
        r"\bsubprocess\.",        # subprocess sin shell_tools
        r"\brequests\.",          # requests síncrono prohibido
    ]

    def __init__(self, file_tools: FileTools, shell_tools: ShellTools, project_root: Path): ...

    async def run(self, mission: Mission) -> Mission:
        """
        Escanea todos los archivos .py listados en MAP.yaml con status="created".
        Genera GuardrailReport y lo guarda en missions/{id}/hulk_report.yaml.
        Si passed == False → lanza HulkViolationError con el reporte.
        Actualiza StateLog y retorna misión.
        """

    async def scan_file(self, file_path: str) -> list[GuardrailViolation]:
        """
        Ejecuta todos los checks sobre un archivo:
        1. _check_line_limit(file_path)   → ViolationType.LINE_LIMIT (severity=error)
        2. _check_imports(file_path)      → via ruff --select F401 (unused imports)
        3. _check_forbidden(file_path)    → regex sobre contenido
        """

    async def _check_line_limit(self, file_path: str) -> GuardrailViolation | None:
        """Usa file_tools.count_lines(). Si > MAX_FILE_LINES → violación error."""

    async def _check_imports(self, file_path: str) -> list[GuardrailViolation]:
        """
        Ejecuta: ruff check {file_path} --select F401 --output-format json
        via shell_tools.run_command().
        Parsea el output JSON de ruff → lista de GuardrailViolation.
        """

    async def _check_forbidden(self, file_path: str) -> list[GuardrailViolation]:
        """
        Lee el contenido del archivo y aplica FORBIDDEN_PATTERNS con re.finditer().
        Cada match → GuardrailViolation severity="error".
        """
```

**Restricciones**:
- Hulk NO modifica código — solo reporta. La modificación es responsabilidad de Widow (Prompt #19).
- Los checks de imports usan `ruff` via `shell_tools` — no parsear AST manualmente.
- **Este archivo NO debe superar 200 líneas.**

---

### TESTS REQUERIDOS: `tests/agents/test_hulk.py`

```python
# Test 1: scan_file detecta archivo > 300L como error
async def test_scan_detects_line_limit_violation(): ...

# Test 2: scan_file detecta open() como forbidden pattern
async def test_scan_detects_forbidden_open(): ...

# Test 3: scan_file limpio → lista vacía
async def test_scan_clean_file_returns_no_violations(): ...

# Test 4: run() lanza HulkViolationError si hay errores
async def test_run_raises_on_errors(): ...

# Test 5: run() no lanza si solo hay warnings
async def test_run_passes_with_only_warnings(): ...

# Test 6: reporte guardado en missions/{id}/hulk_report.yaml
async def test_report_saved_to_correct_path(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `agents/hulk.py` < 200 líneas
- [ ] 4 tipos de violación implementados
- [ ] `ruff` via `shell_tools` para unused imports
- [ ] Regex para patrones prohibidos (open, subprocess, etc.)
- [ ] `HulkViolationError` en `core/exceptions.py` (añadir)
- [ ] 6 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Hulk** | Hulk se escanea a sí mismo — `agents/hulk.py` debe pasar sus propios checks |
| **Widow** | Hulk NO modifica — solo reporta. Modificación = Widow |
| **ROOT JAIL** | `scan_file` usa `file_tools.read_file()` — no `open()` directo |
