# Prompt #23 — El Infiltrado: Colector de Métricas y Feedback → nuevo brief.yaml

**Fase**: 5 — Ciclo de Cierre
**Agente objetivo**: El Infiltrado
**Archivo(s) a crear**:
- `tools/feedback_collector.py` — Colector async de engagement y comentarios
**Dependencias previas**: Prompt #22 (InfiltradoAgent, SocialPost con post_url)
**Checkpoint humano**: No — el feedback se convierte en input de Thor automáticamente

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en análisis de datos sociales
y pipelines de feedback, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → Fase 7 del Bucle Infinito (Evolución: feedback → Thor).
3. Lee `agents/infiltrado.py` → `SocialPost`, `InfiltradoAgent`.
4. Lee `tools/sources/__init__.py` → `PainSignal` (reutilizar para feedback).
5. Lee `agents/thor.py` → `BriefV1` (el output de feedback alimenta a Thor).

---

### TAREA: Implementar el colector de feedback

#### ARCHIVO: `tools/feedback_collector.py`

```python
class FeedbackItem(BaseModel):
    """Un comentario/respuesta real de un usuario al post publicado."""
    source: str                  # "x" | "reddit"
    post_url: str                # URL del post padre
    content: str                 # Texto del comentario
    author: str
    sentiment: str | None = None # "positive" | "negative" | "neutral" — llenado por LLM
    is_feature_request: bool = False
    is_bug_report: bool = False
    engagement: int              # likes/upvotes del comentario
    collected_at: datetime


class FeedbackSummary(BaseModel):
    """Resumen del ciclo de feedback de una misión."""
    mission_id: str
    total_items: int
    positive_ratio: float
    feature_requests: list[str]  # Textos de las solicitudes más votadas
    pain_points: list[str]       # Nuevos dolores identificados
    suggested_keyword: str       # Keyword para la próxima misión de Thor
    generated_at: datetime


class FeedbackCollector:
    """
    Recoge comentarios de los posts publicados y extrae insights para Thor.
    Opera 24-48h después de la publicación (llamado por Nick Fury en el loop closure).
    """

    ANALYSIS_PROMPT: ClassVar[str] = """
    Analiza los siguientes comentarios de usuarios sobre un producto de software.
    Extrae:
    1. Sentiment general (positive/negative/neutral) por comentario.
    2. Feature requests explícitas.
    3. Nuevos dolores/problemas mencionados (que Thor podría investigar).
    4. Una keyword concisa para la próxima búsqueda de Thor.
    Output: JSON con FeedbackSummary. Sin texto libre.
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        x_source: "XSource",
        reddit_source: "RedditSource",
        file_tools: FileTools,
    ): ...

    async def collect(self, posts: list[SocialPost], hours_window: int = 48) -> list[FeedbackItem]:
        """
        Para cada post publicado:
        - X: GET /2/tweets/{post_id}/liking_users + replies via search.
        - Reddit: GET /r/{sub}/comments/{post_id}.json.
        Retorna todos los comentarios como FeedbackItem.
        """

    async def analyze(self, items: list[FeedbackItem], mission_id: str) -> FeedbackSummary:
        """
        Llama al LLM con ANALYSIS_PROMPT + top 30 comentarios (por engagement).
        Parsea respuesta → FeedbackSummary.
        Guarda en missions/{id}/feedback_summary.yaml via file_tools.
        """

    async def to_pain_signals(self, summary: FeedbackSummary) -> list[PainSignal]:
        """
        Convierte feature_requests y pain_points en PainSignal
        para que Thor los use como semilla en la próxima misión.
        source="feedback_loop", engagement basado en votos originales.
        """
```

**Restricciones**:
- `analyze()` recibe solo los **top 30** comentarios por engagement — principio JIT.
- `to_pain_signals()` es el puente entre el Infiltrado y Thor — interfaz crítica del loop.
- **Este archivo NO debe superar 150 líneas.**

---

### TESTS REQUERIDOS: `tests/tools/test_feedback_collector.py`

```python
# Test 1: collect() llama ambas fuentes (X + Reddit) para posts publicados
async def test_collect_calls_all_sources(): ...

# Test 2: analyze() pasa solo top 30 por engagement al LLM (JIT)
async def test_analyze_uses_top_30_signals(): ...

# Test 3: to_pain_signals() genera PainSignal por cada feature request
def test_to_pain_signals_creates_signals(): ...

# Test 4: FeedbackSummary guardado en missions/{id}/
async def test_summary_saved_to_correct_path(): ...

# Test 5: collect() maneja posts sin comentarios (lista vacía)
async def test_collect_handles_empty_responses(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `tools/feedback_collector.py` < 150 líneas
- [ ] `to_pain_signals()` implementado como puente Thor ↔ Infiltrado
- [ ] JIT: máx 30 comentarios al LLM
- [ ] `feedback_summary.yaml` en `missions/{id}/` via `file_tools`
- [ ] 5 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **JIT Context** | Solo top 30 comentarios al LLM — no el hilo completo |
| **ROOT JAIL** | `feedback_summary.yaml` en `missions/{id}/` via `file_tools` |
| **Hulk** | < 150L — si crece, extraer `analyze` a `tools/feedback_analyzer.py` |
| **Widow** | `to_pain_signals` es la única salida pública hacia Thor — nada más |
