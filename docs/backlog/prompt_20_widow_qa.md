# Prompt #20 — Black Widow QA: Runner de Tests y Reporte de Cobertura

**Fase**: 4 — Sistema de Calidad
**Agente objetivo**: Black Widow
**Archivo(s) a crear**:
- `tools/qa_runner.py` — Runner de pytest + reporte de cobertura
**Dependencias previas**: Prompt #19 (BlackWidowAgent, WidowReport), Prompt #13 (TestGenerator)
**Checkpoint humano**: **[👤 HUMANO]** — Validar cobertura mínima (80%) antes de pasar a deploy

---

## 📋 Prompt Completo

---

Actúa como un Senior QA Engineer especializado en automatización de tests y cobertura
de código, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `tools/shell_tools.py` → `run_command` (para pytest).
3. Lee `agents/black_widow.py` → `WidowReport`, cómo Widow usa QARunner.
4. Lee `core/models.py` → `Mission`, `StateLogEntry`.

---

### TAREA: Implementar el runner de QA

#### ARCHIVO: `tools/qa_runner.py`

```python
class TestResult(BaseModel):
    test_id: str          # "tests/core/test_state_log.py::test_ttl"
    passed: bool
    duration_ms: float
    error_message: str | None = None


class CoverageReport(BaseModel):
    total_coverage: float              # 0.0 - 100.0
    per_file: dict[str, float]         # {"core/models.py": 95.3, ...}
    uncovered_lines: dict[str, list[int]]  # líneas sin cobertura por archivo
    meets_threshold: bool              # True si total_coverage >= threshold


class QAReport(BaseModel):
    mission_id: str
    total_tests: int
    passed: int
    failed: int
    errors: int
    duration_seconds: float
    coverage: CoverageReport
    test_results: list[TestResult]
    generated_at: datetime

    @computed_field
    @property
    def success_rate(self) -> float:
        return (self.passed / self.total_tests * 100) if self.total_tests > 0 else 0.0


class QARunner:
    """
    Ejecuta la suite de tests de una misión y genera un QAReport.
    Integra con pytest + pytest-cov via shell_tools.
    """

    MIN_COVERAGE_THRESHOLD: ClassVar[float] = 80.0

    def __init__(
        self,
        file_tools: FileTools,
        shell_tools: ShellTools,
        project_root: Path,
    ): ...

    async def run_suite(self, mission: Mission, test_paths: list[str]) -> QAReport:
        """
        Ejecuta: pytest {test_paths} --cov={src_paths} --cov-report=json
                  --tb=short -q via shell_tools.run_command().
        Parsea el output JSON de pytest y coverage.json.
        Guarda el reporte en missions/{id}/qa_report.yaml.
        Retorna QAReport.
        """

    async def check_threshold(self, report: QAReport) -> bool:
        """
        Verifica que report.coverage.total_coverage >= MIN_COVERAGE_THRESHOLD.
        Si no → loggear qué archivos están por debajo.
        Retorna True si pasa, False si no.
        """

    async def generate_summary(self, report: QAReport) -> str:
        """
        Genera texto legible para el StateLog y el Checkpoint humano.
        Formato:
          "✅ QA PASS — 47/47 tests, 83.2% cobertura
           ❌ QA FAIL — 3 tests fallidos, 71.4% cobertura (mínimo: 80%)"
        """
```

**Restricciones**:
- QARunner NUNCA modifica código — solo ejecuta y reporta.
- El threshold del 80% es configurable via `Settings` pero 80% es el mínimo hard.
- **Este archivo NO debe superar 150 líneas.**
- Si el reporte JSON de pytest/coverage es muy grande, truncar `test_results` a los 50 fallos.

---

### INTEGRACIÓN CON BLACK WIDOW

En `agents/black_widow.py`, el método `run()` termina con:
```python
qa_report = await self.qa_runner.run_suite(mission, test_paths)
if not await self.qa_runner.check_threshold(qa_report):
    # No lanzar excepción — Nick Fury activará Checkpoint humano
    mission = await self.checkpoint_manager.trigger(
        mission, reason=await self.qa_runner.generate_summary(qa_report),
        triggered_by="qa_threshold_not_met", blocking_agent=AgentRole.BLACK_WIDOW
    )
```

---

### TESTS REQUERIDOS: `tests/tools/test_qa_runner.py`

```python
# Test 1: run_suite ejecuta pytest con cobertura (shell_tools mock)
async def test_run_suite_executes_pytest_with_coverage(): ...

# Test 2: check_threshold retorna False si cobertura < 80%
async def test_check_threshold_fails_below_80(): ...

# Test 3: check_threshold retorna True si cobertura >= 80%
async def test_check_threshold_passes_above_80(): ...

# Test 4: generate_summary incluye ✅/❌ según resultado
async def test_generate_summary_format(): ...

# Test 5: QAReport guardado en missions/{id}/qa_report.yaml
async def test_qa_report_saved(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `tools/qa_runner.py` < 150 líneas
- [ ] `CoverageReport.meets_threshold` calculado correctamente
- [ ] `QAReport.success_rate` como `computed_field`
- [ ] Integración con BlackWidowAgent documentada
- [ ] Threshold configurable pero mínimo hard 80%
- [ ] 5 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Hulk** | < 150L — QARunner es una herramienta, no un dios |
| **Widow** | Si cobertura < 80% → Checkpoint humano, no silenciar el fallo |
| **ROOT JAIL** | `shell_tools.run_command(["pytest", ...], cwd=project_root)` |
