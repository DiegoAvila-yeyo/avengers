# Prompt #03 — El Corazón de Nick Fury: Modelos y Estado Global

**Fase**: 1 — Sistema Nervioso Central
**Agente objetivo**: Nick Fury
**Archivo(s) a crear**:
- `core/models.py` — Modelos Pydantic base del sistema
- `core/state_log.py` — Lógica del State Log (TTL, append, truncate)
**Dependencias previas**: Prompt #01 (Settings), Prompt #02 (DB Layer)
**Checkpoint humano**: No — continúa automáticamente hacia Prompt #04

### 🔒 Enmiendas de Resiliencia (v0.3.0)
> Aplicadas por la Refactorización de Requisitos del 2026-03-13.

- **[PERSISTENCIA ESTRICTA]** El `StateLogManager` NO es efímero. Cada `append()` debe
  disparar una sincronización con MongoDB (via el repositorio del Prompt #02) de forma async.
  El contrato: **si no se puede persistir, se lanza `StatePersistenceError`** — nunca se pierde
  un evento en memoria sin respaldo en DB.
- **[RETRY POLICY MODEL]** Añadir el modelo `RetryPolicy` en `core/models.py` para que
  el Prompt #04 (Orquestador) lo use. Ver especificación abajo.

---

## 🎯 Instrucción Principal

```
Lee .github/copilot-instructions.md y ARCHITECTURE.md antes de proponer
cualquier cambio. Respeta el Protocolo Hulk (max 300 líneas por archivo)
y el Protocolo Widow (cero código muerto) sin excepciones.
```

---

## 📋 Prompt Completo (copia y pega en tu sesión de Copilot)

---

Actúa como un Senior Developer Python especializado en Pydantic v2 y arquitecturas
multi-agente, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones de código, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → estructura del Bucle Infinito y el formato del State Log.
3. Lee `pyproject.toml` → dependencias disponibles (pydantic v2, motor, etc.).

---

### TAREA: Crear los modelos base del sistema nervioso de Nick Fury

Debes generar **exactamente dos archivos**. No más.

---

#### ARCHIVO 1: `core/models.py`

Define los siguientes modelos Pydantic v2. Cada campo debe tener:
- Tipo estricto (no `Any`).
- `Field(...)` con `description=` explicativo.
- Validators donde aplique (`@field_validator`).

**Modelos requeridos:**

```python
# 1. MissionStatus — Enum de estados del ciclo de vida
class MissionStatus(str, Enum):
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    AWAITING_HUMAN = "awaiting_human"   # Checkpoint bloqueante
    REVIEW = "review"
    DONE = "done"
    FAILED = "failed"
    ABORTED = "aborted"

# 2. AgentRole — Enum de todos los agentes del sistema
class AgentRole(str, Enum):
    NICK_FURY = "nick_fury"
    THOR = "thor"
    CAPTAIN_AMERICA = "captain_america"
    IRON_CODER = "iron_coder"
    VISION_UI = "vision_ui"
    API_FABRICATOR = "api_fabricator"
    BLACK_WIDOW = "black_widow"
    HULK = "hulk"
    INFILTRADO = "infiltrado"

# 3. StateLogEntry — Una entrada del diario de misión
class StateLogEntry(BaseModel):
    ts: datetime                  # timestamp UTC auto-generado
    agent: AgentRole
    event: str                    # e.g. "brief_generated", "blueprint_approved"
    summary: str                  # Resumen ejecutivo ≤ 500 chars (validar con @field_validator)
    artifact_ref: str | None      # Path relativo al artefacto generado (opcional)
    token_cost: int = 0           # Tokens consumidos en esta operación

# 4. TokenBudget — Control de gasto de API
class TokenBudget(BaseModel):
    total_limit: int = Field(default=500_000, description="Límite total de tokens por misión")
    consumed: int = Field(default=0, ge=0)
    remaining: int                # computed_field: total_limit - consumed
    alert_threshold: float = 0.80 # Alertar cuando consumed/total_limit > threshold

    @computed_field  # type: ignore[misc]
    @property
    def remaining(self) -> int:
        return self.total_limit - self.consumed

    @computed_field  # type: ignore[misc]
    @property
    def is_over_alert(self) -> bool:
        return (self.consumed / self.total_limit) > self.alert_threshold

# 5. MissionBlueprint — El contrato central que Cap. América genera
class MissionBlueprint(BaseModel):
    blueprint_id: str             # UUID generado automáticamente
    mission_id: str
    version: str = "1.0.0"
    product_name: str
    problem_statement: str        # Dolor detectado por Thor
    target_audience: str
    tech_stack: list[str]         # e.g. ["Python 3.12", "FastAPI", "MongoDB"]
    modules: list[str]            # Nombres de módulos a construir
    api_contracts: dict[str, Any] # Endpoints: {"POST /users": {...}}
    acceptance_criteria: list[str]
    created_at: datetime
    approved_by_human: bool = False

# 6. RetryPolicy — Política de reintento de Nick Fury (usada en Prompt #04)
class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=5)
    base_delay_seconds: float = Field(default=2.0, gt=0)
    # backoff: delay = base_delay * (2 ** attempt)
    attempt: int = Field(default=0, ge=0)

    @computed_field  # type: ignore[misc]
    @property
    def next_delay(self) -> float:
        return self.base_delay_seconds * (2 ** self.attempt)

    @computed_field  # type: ignore[misc]
    @property
    def is_exhausted(self) -> bool:
        return self.attempt >= self.max_attempts

# 7. Mission — El objeto central que Nick Fury gestiona
class Mission(BaseModel):
    mission_id: str               # UUID
    status: MissionStatus = MissionStatus.IDLE
    current_phase: int = Field(default=1, ge=1, le=5)
    current_agent: AgentRole = AgentRole.NICK_FURY
    brief_ref: str | None = None
    blueprint_ref: str | None = None
    token_budget: TokenBudget = Field(default_factory=TokenBudget)
    log: list[StateLogEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    output_dir: str               # Directorio relativo en output/
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    current_retry_agent: AgentRole | None = None  # Agente que está siendo reintentado
```

**Restricciones de implementación:**
- Usa `model_config = ConfigDict(frozen=False, validate_assignment=True)` en `Mission`.
- `summary` en `StateLogEntry` debe rechazar strings > 500 caracteres con un `@field_validator`.
- Usa `from __future__ import annotations` para evitar problemas de forward references.
- **Este archivo NO debe superar 150 líneas.** Si se acerca, extrae los Enums a `core/enums.py`.

---

#### ARCHIVO 2: `core/state_log.py`

Implementa la clase `StateLogManager` con las siguientes responsabilidades:

```python
class StateLogManager:
    """
    Gestiona el State Log de una misión con TTL de 50 entradas.
    Principio JIT: solo expone el contexto mínimo necesario para el agente activo.
    """

    MAX_ENTRIES: ClassVar[int] = 50  # TTL del log

    def append(self, mission: Mission, entry: StateLogEntry) -> Mission:
        """
        Añade una entrada al log y trunca a MAX_ENTRIES (FIFO).
        Actualiza mission.updated_at automáticamente.
        ⚠️ [PERSISTENCIA ESTRICTA] — este método es SÍNCRONO solo para la mutación
        en memoria. La sincronización con MongoDB se delega al caller async:
            await repo.save_mission(state_log_manager.append(mission, entry))
        Lanza StatePersistenceError si la misión no tiene mission_id válido.
        """

    def get_jit_context(self, mission: Mission, agent: AgentRole) -> list[StateLogEntry]:
        """
        Retorna SOLO las entradas relevantes para el agente dado.
        Filtra por agent == agent O las últimas 10 entradas globales.
        Esto es la implementación del principio JIT.
        """

    def get_last_artifact(self, mission: Mission, agent: AgentRole) -> str | None:
        """
        Retorna el artifact_ref más reciente del agente dado.
        Útil para que el siguiente agente sepa qué archivo consumir.
        """

    def summarize_for_handoff(self, mission: Mission) -> str:
        """
        Genera un resumen ejecutivo de las últimas MAX_ENTRIES/2 entradas.
        Formato: "Agent X completó Y en Z tokens. Artefacto: path/to/file."
        Este resumen es lo que Nick Fury inyecta al siguiente agente.
        """
```

**Restricciones:**
- Cero dependencias externas en este archivo (solo stdlib + los modelos de `core/models.py`).
- Todos los métodos deben ser **síncronos** (la persistencia en DB es responsabilidad del repositorio, no de este manager).
- **Este archivo NO debe superar 100 líneas.**

---

### TESTS REQUERIDOS: `tests/core/test_state_log.py`

Genera tests pytest que cubran:

```python
# Test 1: TTL — el log no supera MAX_ENTRIES después de 60 appends
def test_state_log_ttl():
    ...

# Test 2: JIT Context — solo devuelve entradas del agente solicitado + últimas 10
def test_jit_context_filters_by_agent():
    ...

# Test 3: Validator — summary > 500 chars lanza ValidationError
def test_summary_max_length_validation():
    ...

# Test 4: TokenBudget computed fields — remaining y is_over_alert son correctos
def test_token_budget_computed_fields():
    ...

# Test 5: get_last_artifact — retorna None si el agente no tiene entradas
def test_get_last_artifact_returns_none_for_unknown_agent():
    ...

# Test 6: summarize_for_handoff — el output contiene los campos esperados
def test_summarize_for_handoff_format():
    ...
```

**Cobertura mínima**: 90% de `core/state_log.py`.

---

### CHECKLIST DE ENTREGA (el agente debe verificar antes de responder)

- [ ] `core/models.py` existe y tiene < 150 líneas (mover Enums a `core/enums.py` si supera)
- [ ] `RetryPolicy` model incluido con `next_delay` y `is_exhausted` como `computed_field`
- [ ] `Mission` incluye `retry_policy` y `current_retry_agent`
- [ ] `core/state_log.py` existe y tiene < 100 líneas
- [ ] `tests/core/test_state_log.py` con 6 tests
- [ ] `ruff check core/ tests/core/` sin errores
- [ ] `mypy core/` sin errores en modo strict
- [ ] Ningún `Any` sin justificación comentada
- [ ] Ningún import sin usar
- [ ] `summarize_for_handoff` produce output legible por un LLM sin ambigüedad

---

### ARTEFACTO ESPERADO AL FINAL

Al terminar, escribe en el State Log de la misión:

```yaml
agent: nick_fury
event: core_models_created
summary: "Modelos base creados: Mission, MissionBlueprint, StateLogEntry, TokenBudget. StateLogManager implementado con TTL=50 y JIT context. 6 tests pasando. Cobertura: XX%."
artifact_ref: "core/models.py"
```

---

### ⚠️ RECUERDA — Protocolos Activos

| Protocolo | Acción si se viola |
|---|---|
| **Hulk** (> 300 líneas) | DETENTE. Propón modularización antes de escribir. |
| **Widow** (código muerto) | Elimina sin preguntar. Documenta qué eliminaste. |
| **JIT** (contexto mínimo) | Si necesitas leer más de 2 archivos externos, algo está mal. |
