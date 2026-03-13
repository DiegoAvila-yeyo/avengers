# Prompt #04 — Motor del Orquestador: Nick Fury Dispatcher

**Fase**: 1 — Sistema Nervioso Central
**Agente objetivo**: Nick Fury
**Archivo(s) a crear**:
- `agents/nick_fury.py` — Orquestador principal (ciclo de vida + dispatcher)
- `core/exceptions.py` — Excepciones del sistema (incluye `StatePersistenceError`)
**Dependencias previas**: Prompt #03 (modelos + StateLogManager)
**Checkpoint humano**: **[👤 HUMANO]** — Validar lógica de dispatch antes de conectar agentes reales

### 🔒 Enmiendas de Resiliencia (v0.3.0)
- **[FURY RETRY LOGIC]** Nick Fury debe reintentar cada agente fallido hasta 3 veces
  con backoff exponencial usando `RetryPolicy.next_delay`. Ver especificación completa abajo.
- **[PERSISTENCIA ESTRICTA]** Todo cambio de `mission.status` debe ser seguido
  inmediatamente de `await repo.save_mission(mission)`. Si falla la persistencia,
  la operación entera se revierte y se marca como `FAILED`.

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en orquestadores async y arquitecturas
multi-agente, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → Protocolos Hulk y Widow.
2. Lee `ARCHITECTURE.md` → Bucle Infinito, fases 1-5, State Log.
3. Lee `core/models.py` → `Mission`, `MissionStatus`, `AgentRole`, `RetryPolicy`.
4. Lee `core/state_log.py` → `StateLogManager`.

---

### TAREA: Crear el motor del orquestador de Nick Fury

#### ARCHIVO 1: `core/exceptions.py`

Define las excepciones del sistema:

```python
class AvengersBaseError(Exception): ...

class StatePersistenceError(AvengersBaseError):
    """Fallo al sincronizar el State Log con MongoDB."""

class AgentExecutionError(AvengersBaseError):
    """Un agente terminó con error no recuperable."""
    def __init__(self, agent: AgentRole, reason: str, attempt: int): ...

class RetryExhaustedError(AvengersBaseError):
    """Nick Fury agotó los 3 reintentos de un agente."""
    def __init__(self, agent: AgentRole, mission_id: str): ...

class BlueprintNotApprovedError(AvengersBaseError):
    """Se intentó ejecutar Fase 3 sin Blueprint aprobado por humano."""

class RootJailViolationError(AvengersBaseError):
    """Un tool intentó acceder a una ruta fuera del proyecto. [ROOT JAIL]"""
```

**Límite**: este archivo NO debe superar 60 líneas.

---

#### ARCHIVO 2: `agents/nick_fury.py`

Implementa `NickFuryOrchestrator` con la siguiente interfaz:

```python
class NickFuryOrchestrator:
    """
    Orquestador central. Gestiona el ciclo de vida de misiones.
    Principio: Nick Fury no ejecuta — coordina y persiste.
    """

    def __init__(self, repo: MissionRepository, state_log: StateLogManager): ...

    async def create_mission(self, output_dir: str) -> Mission:
        """Crea y persiste una nueva misión con status=IDLE."""

    async def dispatch(self, mission: Mission, agent: AgentRole) -> Mission:
        """
        Despacha al agente dado aplicando FURY RETRY LOGIC:

        Algoritmo:
        1. Intentar ejecutar `agent.run(mission)` (el agente se inyecta como callable).
        2. Si falla con AgentExecutionError:
           a. Si retry_policy.is_exhausted → cambiar status=FAILED, persistir,
              lanzar RetryExhaustedError y esperar intervención humana.
           b. Si no agotado → incrementar attempt, esperar next_delay segundos
              (asyncio.sleep), reintentar desde paso 1.
        3. Si éxito → reset retry_policy, actualizar status, persistir y retornar.

        El delay entre reintentos es EXPONENCIAL: 2s, 4s, 8s (base_delay=2, máx 3 intentos).
        """

    async def advance_phase(self, mission: Mission) -> Mission:
        """
        Avanza mission.current_phase en 1.
        BLOQUEO: si current_phase va de 2 → 3, verificar blueprint_ref != None
        y mission.approved_by_human == True. Si no, lanzar BlueprintNotApprovedError.
        Persistir inmediatamente tras el avance.
        """

    async def mark_awaiting_human(self, mission: Mission, reason: str) -> Mission:
        """Cambia status a AWAITING_HUMAN, registra reason en StateLog, persiste."""

    async def resume_from_checkpoint(self, mission_id: str) -> Mission:
        """
        Recupera misión desde MongoDB por mission_id.
        Útil para continuar tras un reinicio del proceso.
        Verifica integridad: si status=IN_PROGRESS y log vacío → marcar FAILED.
        """
```

**Restricciones**:
- Todos los métodos que mutan `Mission` deben llamar `await repo.save_mission(mission)`
  antes de retornar. Sin excepciones. Esto es la **Persistencia Estricta**.
- `dispatch` debe usar `asyncio.sleep(mission.retry_policy.next_delay)` — no `time.sleep`.
- `NickFuryOrchestrator` NO importa ningún agente concreto (Thor, Cap, etc.).
  Recibe un `Callable[[Mission], Awaitable[Mission]]` como agente — desacoplamiento total.
- **Este archivo NO debe superar 200 líneas.**

---

### TESTS REQUERIDOS: `tests/agents/test_nick_fury.py`

```python
# Test 1: dispatch exitoso en primer intento — retry_policy.attempt == 0
async def test_dispatch_success_first_attempt(): ...

# Test 2: dispatch con 2 fallos y éxito en 3er intento
async def test_dispatch_retries_on_failure(): ...

# Test 3: dispatch agota reintentos → lanza RetryExhaustedError, status=FAILED
async def test_dispatch_exhausted_raises_and_marks_failed(): ...

# Test 4: advance_phase de 2→3 sin blueprint aprobado → BlueprintNotApprovedError
async def test_advance_phase_blocks_without_approved_blueprint(): ...

# Test 5: cada cambio de estado llama repo.save_mission (mock verify)
async def test_every_state_change_persists(): ...

# Test 6: resume_from_checkpoint recupera misión desde repo
async def test_resume_from_checkpoint(): ...

# Test 7: backoff delay es exponencial (2s, 4s, 8s) — mockear asyncio.sleep
async def test_exponential_backoff_delays(): ...
```

**Cobertura mínima**: 90% de `agents/nick_fury.py`.

---

### CHECKLIST DE ENTREGA

- [ ] `core/exceptions.py` < 60 líneas, todas las excepciones documentadas
- [ ] `agents/nick_fury.py` < 200 líneas
- [ ] Retry Logic: 3 intentos, backoff exponencial, status=FAILED al agotar
- [ ] Persistencia Estricta: `repo.save_mission()` en cada mutación de estado
- [ ] `BlueprintNotApprovedError` lanzada en phase 2→3 sin aprobación humana
- [ ] 7 tests passing, cobertura ≥ 90%
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Hulk** (> 300L) | DETENTE, modulariza |
| **Widow** (código muerto) | Elimina antes de entregar |
| **Fury Retry** | `base_delay=2`, `max_attempts=3`, backoff `2^n` |
| **Persistencia Estricta** | `repo.save_mission()` es obligatorio, no opcional |
