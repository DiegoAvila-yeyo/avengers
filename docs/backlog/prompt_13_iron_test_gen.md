# Prompt #13 — Iron-Coder Tests: Generador Automático de Tests pytest

**Fase**: 3 — La Fábrica
**Agente objetivo**: Iron-Coder
**Archivo(s) a crear**:
- `tools/test_generator.py` — Generador automático de tests pytest por módulo
**Dependencias previas**: Prompt #12 (IronCoderAgent, MAP.yaml), Prompt #11 (file_tools)
**Checkpoint humano**: No

### 🔒 Cláusula ROOT JAIL (v0.3.0) — OBLIGATORIA
**Toda operación de escritura de archivos de test DEBE usar `tools.file_tools.write_file()`.
El generador NUNCA escribe fuera de `tests/` dentro del project_root.
Lanzar `RootJailViolationError` ante cualquier intento de escritura en ruta no permitida.**

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en testing y generación de código,
trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolos Hulk y Widow.
2. Lee `core/blueprint_schema.py` → `AcceptanceCriterion.automated`, `ModuleSpec`.
3. Lee `tools/file_tools.py` → `write_file`, `resolve_safe_path`.
4. Lee `missions/{mission_id}/MAP.yaml` → qué módulos existen y sus rutas.

---

### TAREA: Implementar el generador de tests

#### ARCHIVO: `tools/test_generator.py`

```python
class TestGenerator:
    """
    Genera archivos pytest automáticamente para cada módulo del Blueprint.
    Fuente de verdad: AcceptanceCriteria con automated=True del BlueprintV1.
    """

    TEST_SYSTEM_PROMPT: ClassVar[str] = """
    Eres un QA Engineer Senior. Genera tests pytest para el módulo dado.
    Reglas:
    - Un test por AcceptanceCriterion con automated=True.
    - Usa pytest-asyncio para endpoints FastAPI (async def test_...).
    - Mocka dependencias externas con pytest-mock o httpx.MockTransport.
    - Nombres descriptivos: test_{criterio_en_snake_case}.
    - Incluye al menos un test de error/edge case por endpoint.
    - Cobertura mínima: 80% del módulo objetivo.
    - NO importes módulos que no estén en pyproject.toml.
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        file_tools: FileTools,
        project_root: Path,
    ): ...

    async def generate_for_module(
        self,
        module_spec: "ModuleSpec",
        module_source: str,            # Contenido del archivo generado por Iron-Coder
        criteria: list["AcceptanceCriterion"],
        mission_id: str,
    ) -> Path:
        """
        1. Filtrar criteria donde automated=True.
        2. Llamar LLM con TEST_SYSTEM_PROMPT + module_source + criteria filtrados.
        3. Parsear el código generado.
        4. Guardar en tests/{module_spec.module_name}/test_{module_spec.module_name}.py
           usando file_tools.write_file() — ROOT JAIL activo.
        5. Verificar que el archivo generado no supere 300 líneas (Hulk check).
           Si supera → dividir en test_{module_name}_part1.py, _part2.py, etc.
        6. Retornar la ruta del archivo de test creado.
        """

    async def run_and_report(self, test_path: str, project_root: Path) -> dict[str, Any]:
        """
        Ejecuta `pytest {test_path} --tb=short --json-report` usando shell_tools.
        Retorna dict con: {"passed": int, "failed": int, "coverage": float, "errors": list[str]}
        Lanza AgentExecutionError si return_code != 0 y failed > 0.
        """
```

**Restricciones**:
- Los tests generados deben escribirse SIEMPRE en `tests/` (subdirectorio del project_root).
- `run_and_report` usa `shell_tools.run_command(["pytest", ...], ...)` — no `subprocess` directo.
- **Este archivo NO debe superar 120 líneas.**

---

### TESTS REQUERIDOS: `tests/tools/test_test_generator.py`

```python
# Test 1: genera archivo de test con un test por AC automated=True
async def test_generates_one_test_per_automated_criterion(): ...

# Test 2: AC con automated=False ignorado
def test_skips_non_automated_criteria(): ...

# Test 3: archivo de test > 300L → dividido en _part1, _part2
async def test_splits_large_test_file(): ...

# Test 4: test escrito en tests/ (ROOT JAIL — no fuera del proyecto)
async def test_writes_only_inside_tests_directory(): ...

# Test 5: run_and_report usa shell_tools (no subprocess directo)
async def test_run_uses_shell_tools(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `tools/test_generator.py` < 120 líneas
- [ ] Escritura SOLO en `tests/` via `file_tools`
- [ ] Split automático de test files > 300L
- [ ] `run_and_report` usa `shell_tools.run_command`
- [ ] 5 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | Tests escritos SOLO en `tests/` via `file_tools` |
| **Hulk** | Test files > 300L → split automático |
| **Widow** | AC no automatizados → ignorar, no generar test vacío |
