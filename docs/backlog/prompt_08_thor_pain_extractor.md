# Prompt #08 — Thor LLM: Extractor de Dolores y Generación de brief.yaml

**Fase**: 2 — Equipo de Estrategia
**Agente objetivo**: Thor
**Archivo(s) a crear**:
- `agents/thor.py` — Agente Thor completo: orquesta scraping + extracción LLM → brief.yaml
**Dependencias previas**: Prompt #06 (Scraper), Prompt #07 (Sources), Prompt #04 (retry logic)
**Checkpoint humano**: **[👤 HUMANO]** — Validar calidad del research antes de que Cap diseñe el Blueprint

### 🔒 Enmiendas Aplicadas
- **AMD-01 Root Jail**: `brief.yaml` escrito en `missions/{id}/brief.yaml` via `file_tools`.
- **AMD-02 Fury Retry Logic**: `ThorAgent.run()` implementa la interfaz `Callable[[Mission], Awaitable[Mission]]` que Nick Fury reintentará hasta 3 veces si falla.

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en agentes LLM y extracción de
información estructurada, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → Fase 1 del Bucle Infinito, rol de Thor.
3. Lee `tools/sources/__init__.py` → `PainSignal`, `SourceConnector`.
4. Lee `tools/file_tools.py` → `write_file` (ROOT JAIL).
5. Lee `core/models.py` → `Mission`, `StateLogEntry`, `AgentRole`.

---

### TAREA: Implementar el agente Thor completo

#### ARCHIVO: `agents/thor.py`

```python
class BriefV1(BaseModel):
    """El artefacto de salida de Thor — input de Cap. América."""
    brief_id: str
    mission_id: str
    keyword: str                      # Keyword inicial de búsqueda
    problem_statement: str            # Dolor principal detectado (≤ 200 chars)
    evidence: list[str]               # URLs de las fuentes más relevantes (max 10)
    pain_signals: list[PainSignal]    # Top 20 señales por engagement
    target_audience: str              # "Developers / SMB owners / etc."
    competitors: list[str]            # Soluciones existentes detectadas
    opportunity_score: float          # 0.0-1.0 — estimado por LLM
    created_at: datetime


class ThorAgent:
    """
    Thor: el cazador de tendencias del internet profundo.
    Orquesta scraping multi-fuente → síntesis LLM → brief.yaml.
    """

    EXTRACTION_PROMPT: ClassVar[str] = """
    Eres un analista de mercado experto. Analiza las siguientes señales de dolor
    de usuarios reales y extrae un problema de negocio concreto.

    Salida: JSON estricto con el schema BriefV1. Sin texto libre.
    Campos obligatorios: problem_statement, target_audience, competitors, opportunity_score.

    Reglas:
    - problem_statement: una frase accionable (no vaga como "la gente quiere X").
    - opportunity_score: 0.0 (saturado/trivial) a 1.0 (nicho sin solución clara).
    - competitors: máximo 5, con nombre real y URL si es posible.
    - target_audience: específico (no "todo el mundo").
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        sources: list[SourceConnector],  # Reddit, X, HN — inyectados
        file_tools: FileTools,
        project_root: Path,
    ): ...

    async def run(self, mission: Mission) -> Mission:
        """
        Interfaz estándar para Nick Fury. Orquesta:
        1. Leer keyword desde mission (en StateLog o primer entry).
        2. Llamar _collect_signals(keyword) → lista de PainSignal.
        3. Llamar _extract_brief(signals, keyword) → BriefV1.
        4. Serializar a YAML → guardar en missions/{mission_id}/brief.yaml (ROOT JAIL).
        5. Actualizar mission.brief_ref, agregar StateLogEntry, retornar misión.
        """

    async def _collect_signals(
        self, keyword: str, limit_per_source: int = 25
    ) -> list[PainSignal]:
        """
        Llama search(keywords=[keyword]) en todas las fuentes en paralelo.
        Combina resultados y ordena por engagement DESC.
        Retorna top 50 señales.
        """

    async def _extract_brief(
        self, signals: list[PainSignal], keyword: str, mission_id: str
    ) -> BriefV1:
        """
        Construye el prompt con las top 20 señales (JIT context — no las 50 completas).
        Llama al LLM. Parsea respuesta → BriefV1 (validación Pydantic automática).
        Si parseo falla → reintentar con el error como feedback (máx 2 veces).
        Si sigue fallando → lanzar AgentExecutionError para Fury.
        """
```

**Restricciones**:
- `run()` es la única interfaz pública hacia Nick Fury. Todo lo demás es privado.
- El prompt al LLM incluye **máximo 20 PainSignals** — principio JIT.
- **Este archivo NO debe superar 180 líneas.**
- Si crece, extraer `BriefV1` a `core/brief_schema.py`.

---

### ARTEFACTO GENERADO

```
missions/
└── {mission_id}/
    └── brief.yaml    ← BriefV1 serializado (input para Cap. América)
```

---

### TESTS REQUERIDOS: `tests/agents/test_thor.py`

```python
# Test 1: run() genera brief.yaml en la ruta correcta
async def test_run_generates_brief_yaml(): ...

# Test 2: _collect_signals llama todas las fuentes en paralelo
async def test_collect_signals_calls_all_sources(): ...

# Test 3: _extract_brief reintenta si LLM devuelve JSON inválido
async def test_extract_brief_retries_on_invalid_json(): ...

# Test 4: si LLM falla 2 veces → AgentExecutionError
async def test_extract_brief_raises_after_max_retries(): ...

# Test 5: brief.yaml escrito via file_tools (ROOT JAIL verificado con mock)
async def test_brief_written_via_file_tools(): ...

# Test 6: señales ordenadas por engagement DESC antes del LLM call
def test_signals_sorted_by_engagement(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `agents/thor.py` < 180 líneas
- [ ] `BriefV1` definido (o en `core/brief_schema.py` si supera límites)
- [ ] `run()` implementa la interfaz `Callable[[Mission], Awaitable[Mission]]`
- [ ] Top 20 señales en prompt LLM (JIT — no las 50)
- [ ] `brief.yaml` en `missions/{id}/` via `file_tools`
- [ ] 6 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | brief.yaml en `missions/{id}/` via `file_tools` |
| **Fury Retry** | `run()` lanza `AgentExecutionError` — Fury gestiona los reintentos externos |
| **JIT Context** | Máximo 20 señales al LLM — no inyectar las 50 |
| **Hulk** | < 180L — si crece, extraer BriefV1 |
