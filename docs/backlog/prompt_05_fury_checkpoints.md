# Prompt #05 — Sistema de Checkpoints: Pausa y Aprobación Humana

**Fase**: 1 — Sistema Nervioso Central
**Agente objetivo**: Nick Fury
**Archivo(s) a crear**:
- `core/checkpoints.py` — Motor de checkpoints: pausar, notificar, reanudar
**Dependencias previas**: Prompt #04 (NickFuryOrchestrator, excepciones)
**Checkpoint humano**: **[👤 HUMANO]** — Confirmar el flujo de aprobación antes de la Fase 2

### 🔒 Enmiendas de Resiliencia (v0.3.0)
- **[FURY RETRY LOGIC — CONTEXTO]** Los checkpoints son el mecanismo que activa Nick Fury
  cuando `RetryExhaustedError` es lanzado. El checkpoint registra el fallo y bloquea el
  avance hasta que un humano revisa y decide: `resume` o `abort`.
- **[PERSISTENCIA ESTRICTA]** El estado `AWAITING_HUMAN` debe persistirse en MongoDB
  antes de notificar al humano. Si la notificación falla, el estado en DB es la fuente de verdad.

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en sistemas de control de flujo async,
trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → Protocolos Hulk y Widow.
2. Lee `ARCHITECTURE.md` → Checkpoints del Bucle Infinito.
3. Lee `core/models.py` → `Mission`, `MissionStatus.AWAITING_HUMAN`.
4. Lee `agents/nick_fury.py` → `NickFuryOrchestrator.mark_awaiting_human()`.
5. Lee `core/exceptions.py` → `RetryExhaustedError`.

---

### TAREA: Crear el sistema de Checkpoints

#### ARCHIVO: `core/checkpoints.py`

```python
# Modelo de un Checkpoint registrado
class CheckpointRecord(BaseModel):
    checkpoint_id: str            # UUID
    mission_id: str
    triggered_by: str             # "retry_exhausted" | "phase_gate" | "manual"
    blocking_agent: AgentRole
    reason: str                   # Descripción legible para el humano
    retry_attempts: int           # Cuántos reintentos se hicieron antes de parar
    created_at: datetime
    resolved_at: datetime | None = None
    resolution: str | None = None # "resume" | "abort" | "retry_override"

class CheckpointManager:
    """
    Gestiona los Checkpoints bloqueantes del sistema AVENGERS.
    Un Checkpoint = punto donde el humano tiene control total.
    """

    def __init__(self, repo: MissionRepository, notifier: "CheckpointNotifier"): ...

    async def trigger(
        self,
        mission: Mission,
        reason: str,
        triggered_by: str,
        blocking_agent: AgentRole,
        retry_attempts: int = 0,
    ) -> CheckpointRecord:
        """
        1. Crea CheckpointRecord y lo persiste en MongoDB.
        2. Cambia mission.status → AWAITING_HUMAN (via nick_fury.mark_awaiting_human).
        3. Llama notifier.notify(checkpoint) para alertar al humano.
        4. Retorna el CheckpointRecord creado.
        Garantía: si notifier.notify() falla, el estado en DB ya está guardado.
        """

    async def resolve(
        self,
        checkpoint_id: str,
        resolution: str,  # "resume" | "abort" | "retry_override"
        mission: Mission,
    ) -> Mission:
        """
        Resuelve un checkpoint:
        - "resume"         → mission.status = IN_PROGRESS, continúa desde current_phase
        - "abort"          → mission.status = ABORTED
        - "retry_override" → reset retry_policy, re-despacha al blocking_agent
        Persiste en MongoDB antes de retornar.
        """

    async def get_pending(self, mission_id: str) -> list[CheckpointRecord]:
        """Retorna checkpoints sin resolver para una misión."""


class CheckpointNotifier(Protocol):
    """
    Interfaz de notificación (desacoplada del canal).
    Implementaciones: ConsolePrinter (dev) | SlackNotifier | EmailNotifier (prod).
    """
    async def notify(self, checkpoint: CheckpointRecord) -> None: ...


class ConsoleCheckpointNotifier:
    """Implementación dev: imprime el checkpoint en consola con formato claro."""
    async def notify(self, checkpoint: CheckpointRecord) -> None:
        # Formato: "⚠️  CHECKPOINT [{id}] — Misión {mission_id}\n  Razón: {reason}\n  Acción requerida: ..."
        ...
```

**Restricciones**:
- `CheckpointRecord` debe guardarse en una colección MongoDB separada: `checkpoints`.
- `CheckpointManager` NO tiene lógica de negocio de los agentes — solo orquesta el pause/resume.
- **Este archivo NO debe superar 150 líneas.**

---

### TESTS REQUERIDOS: `tests/core/test_checkpoints.py`

```python
# Test 1: trigger → crea CheckpointRecord, persiste, mission.status=AWAITING_HUMAN
async def test_trigger_creates_record_and_sets_awaiting(): ...

# Test 2: trigger → notifier.notify() llamado con el checkpoint correcto
async def test_trigger_calls_notifier(): ...

# Test 3: trigger con notifier fallido → CheckpointRecord YA persistido en DB
async def test_trigger_persists_even_if_notifier_fails(): ...

# Test 4: resolve "resume" → mission.status = IN_PROGRESS
async def test_resolve_resume_sets_in_progress(): ...

# Test 5: resolve "abort" → mission.status = ABORTED
async def test_resolve_abort_sets_aborted(): ...

# Test 6: resolve "retry_override" → retry_policy reseteada
async def test_resolve_retry_override_resets_policy(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `core/checkpoints.py` < 150 líneas
- [ ] `CheckpointNotifier` es un `Protocol`, no una clase base
- [ ] `ConsoleCheckpointNotifier` implementado para dev/testing
- [ ] Persistencia en colección `checkpoints` separada de `missions`
- [ ] 6 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Hulk** (> 300L) | DETENTE, modulariza |
| **Widow** | Cero código muerto antes de entregar |
| **Persistencia Estricta** | Estado en DB ANTES de notificar |
