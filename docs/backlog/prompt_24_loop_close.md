# Prompt #24 — Loop Closure: Nick Fury Lanza la Siguiente Misión (∞)

**Fase**: 5 — Ciclo de Cierre
**Agente objetivo**: Nick Fury
**Archivo(s) a crear**:
- `tools/loop_manager.py` — Gestor del cierre de misión y apertura del nuevo ciclo
**Dependencias previas**: Prompt #23 (FeedbackSummary, PainSignals), Prompt #04 (NickFuryOrchestrator)
**Checkpoint humano**: **[👤 HUMANO]** — Autorizar gasto de tokens para el nuevo ciclo

---

## 📋 Prompt Completo

---

Actúa como un Senior Software Architect especializado en sistemas de bucles infinitos
y orquestación de agentes, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → Sección completa del Bucle Infinito y el Loop Closure.
3. Lee `agents/nick_fury.py` → `NickFuryOrchestrator.create_mission()`.
4. Lee `tools/feedback_collector.py` → `FeedbackSummary`, `to_pain_signals()`.
5. Lee `core/models.py` → `Mission`, `MissionStatus`, `TokenBudget`.
6. Lee `core/checkpoints.py` → `CheckpointManager` (aprobación del nuevo ciclo).

---

### TAREA: Implementar el cierre de ciclo y el loop infinito

#### ARCHIVO: `tools/loop_manager.py`

```python
class MissionSummary(BaseModel):
    """Resumen ejecutivo de una misión completada para el archivo histórico."""
    mission_id: str
    product_name: str
    status: MissionStatus
    total_tokens_used: int
    total_duration_seconds: float
    artifacts_created: int          # Archivos en MAP.yaml con status="created"
    tests_passing: int
    coverage_pct: float
    deploy_url: str | None
    feedback_summary_ref: str | None
    closed_at: datetime


class LoopManager:
    """
    Gestiona el cierre ordenado de una misión y el arranque de la siguiente.
    Nick Fury delega aquí la lógica del Bucle Infinito.
    """

    def __init__(
        self,
        orchestrator: "NickFuryOrchestrator",
        checkpoint_manager: "CheckpointManager",
        file_tools: FileTools,
        repo: MissionRepository,
    ): ...

    async def close_mission(self, mission: Mission) -> MissionSummary:
        """
        Cierre ordenado de una misión completada:
        1. Cambiar mission.status → DONE.
        2. Generar MissionSummary con métricas del State Log.
        3. Guardar summary en missions/{id}/mission_summary.yaml.
        4. Archivar el MAP.yaml en output/{id}/MAP_final.yaml.
        5. Persistir en MongoDB (AMD-05 Strict Persistence).
        6. Limpiar output/scrape_cache/{id}/ (datos temporales).
        7. Retornar MissionSummary.
        """

    async def evaluate_next_cycle(
        self,
        summary: MissionSummary,
        feedback: "FeedbackSummary",
    ) -> bool:
        """
        Decide si vale la pena lanzar un nuevo ciclo basado en:
        - feedback.positive_ratio > 0.4 (producto tuvo tracción)
        - summary.coverage_pct >= 80.0 (calidad mínima alcanzada)
        - summary.total_tokens_used < token_budget.total_limit * 0.9 (margen de presupuesto)
        Retorna True si se recomienda continuar el bucle.
        """

    async def launch_next_cycle(
        self,
        prev_summary: MissionSummary,
        feedback: "FeedbackSummary",
    ) -> Mission:
        """
        Inicia la siguiente iteración del Bucle Infinito:
        1. Trigger Checkpoint humano → esperar autorización de gasto.
        2. Crear nueva misión con orchestrator.create_mission().
        3. Inyectar feedback.suggested_keyword como primer StateLogEntry.
        4. Inyectar feedback.to_pain_signals() como contexto inicial de Thor.
        5. Persistir la nueva misión.
        6. Retornar la nueva misión (Nick Fury la despachará a Thor).

        Si evaluate_next_cycle() retorna False → no crear nueva misión,
        solo registrar en logs: "Bucle pausado — tracción insuficiente".
        """

    async def generate_factory_report(self) -> str:
        """
        Genera un reporte de rendimiento de la factoría completa:
        - Misiones completadas vs fallidas
        - Tokens consumidos en total
        - Productos desplegados
        - Tiempo promedio Brief → Deploy
        Lee de MongoDB todas las misiones con status=DONE.
        Guarda en docs/factory_report.md.
        """
```

**Restricciones**:
- `launch_next_cycle()` tiene el Checkpoint humano como primera instrucción — es bloqueante.
- `close_mission()` limpia el scrape_cache — los datos scrapeados son efímeros, no los blueprints.
- **Este archivo NO debe superar 180 líneas.**

---

### FLUJO COMPLETO DEL LOOP (diagrama textual)

```
Mission DONE
     ↓
close_mission() → MissionSummary
     ↓
evaluate_next_cycle() → True / False
     ↓ True
[👤 HUMANO] Checkpoint: "¿Autorizar nueva misión? Costo estimado: ~$X"
     ↓ Aprobado
launch_next_cycle() → Nueva Mission con keyword de feedback
     ↓
NickFuryOrchestrator.dispatch(nueva_mission, AgentRole.THOR)
     ↓
∞ El ciclo comienza de nuevo
```

---

### TESTS REQUERIDOS: `tests/tools/test_loop_manager.py`

```python
# Test 1: close_mission() cambia status a DONE y guarda summary
async def test_close_mission_sets_done_and_saves_summary(): ...

# Test 2: close_mission() limpia scrape_cache pero NO blueprints
async def test_close_mission_cleans_cache_not_blueprints(): ...

# Test 3: evaluate_next_cycle() retorna False si positive_ratio < 0.4
def test_evaluate_returns_false_on_low_traction(): ...

# Test 4: launch_next_cycle() crea checkpoint antes de nueva misión
async def test_launch_triggers_checkpoint_first(): ...

# Test 5: launch_next_cycle() inyecta keyword de feedback en StateLog
async def test_launch_injects_feedback_keyword(): ...

# Test 6: generate_factory_report() lee todas las misiones DONE y escribe doc
async def test_factory_report_aggregates_completed_missions(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `tools/loop_manager.py` < 180 líneas
- [ ] `close_mission()` limpia cache sin tocar blueprints/outputs
- [ ] `evaluate_next_cycle()` con las 3 condiciones documentadas
- [ ] `launch_next_cycle()` con Checkpoint humano como primera instrucción
- [ ] `generate_factory_report()` guardado en `docs/factory_report.md`
- [ ] 6 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Checkpoint Humano** | `launch_next_cycle()` SIEMPRE solicita aprobación de gasto |
| **AMD-05 Persistencia** | `close_mission()` persiste en MongoDB antes de retornar |
| **ROOT JAIL** | Todo I/O via `file_tools` |
| **Hulk** | < 180L — si crece, extraer `generate_factory_report` a `tools/reporter.py` |
| **Widow** | `evaluate_next_cycle()` es la única lógica de decisión — centralizada aquí |
