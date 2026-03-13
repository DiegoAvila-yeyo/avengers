# Prompt #07 — Thor Sources: Conectores Reddit, X/Twitter, HackerNews

**Fase**: 2 — Equipo de Estrategia
**Agente objetivo**: Thor
**Archivo(s) a crear**:
- `tools/sources/reddit_source.py` — Conector Reddit (PRAW/API)
- `tools/sources/x_source.py` — Conector X/Twitter API v2
- `tools/sources/hackernews_source.py` — Conector HackerNews API (pública)
**Dependencias previas**: Prompt #06 (DynamicScraper), Prompt #01 (Settings)
**Checkpoint humano**: No

### 🔒 Enmienda AMD-01 Root Jail
Los datos crudos descargados de estas fuentes se cachean ÚNICAMENTE en
`output/scrape_cache/{source}/{mission_id}/` via `file_tools.write_file()`.

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en integración de APIs de redes
sociales y fuentes de datos públicas, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → rol de Thor como Trend-Hunter del "internet profundo".
3. Lee `core/settings.py` → `reddit_client_id`, `x_api_key` y sus secrets.
4. Lee `tools/scraper.py` → `ScrapedPage`, `DynamicScraper`.

---

### TAREA: Crear los conectores de fuentes

#### INTERFAZ COMÚN (definir en `tools/sources/__init__.py`):

```python
class PainSignal(BaseModel):
    """Señal de dolor detectada en una fuente."""
    source: str               # "reddit" | "x" | "hackernews"
    content: str              # Texto del post/comentario/pregunta
    url: str
    engagement: int           # Upvotes, likes, puntos — proxy de relevancia
    author: str
    collected_at: datetime
    keywords: list[str]       # Tags o flair detectados


class SourceConnector(Protocol):
    """Protocolo común para todos los conectores de Thor."""
    async def search(self, keywords: list[str], limit: int) -> list[PainSignal]: ...
    async def get_trending(self, category: str, limit: int) -> list[PainSignal]: ...
```

#### ARCHIVO 1: `tools/sources/reddit_source.py`

```python
class RedditSource:
    """
    Conector Reddit via API (OAuth2).
    Busca en subreddits relevantes por keywords. Prioriza posts con alto engagement.
    """
    BASE_URL = "https://oauth.reddit.com"

    def __init__(self, settings: Settings, scraper: DynamicScraper): ...

    async def _get_token(self) -> str:
        """OAuth2 client credentials flow. Cachea el token hasta expiración."""

    async def search(self, keywords: list[str], limit: int = 25) -> list[PainSignal]:
        """
        Busca posts usando /search.json con parámetros: q, sort=top, t=month.
        Convierte cada post en PainSignal con engagement=score.
        """

    async def get_trending(self, category: str, limit: int = 10) -> list[PainSignal]:
        """
        Extrae posts trending de subreddits predefinidos por categoría.
        Usa /r/{subreddit}/hot.json.
        """
```

#### ARCHIVO 2: `tools/sources/x_source.py`

```python
class XSource:
    """
    Conector X/Twitter API v2 (Bearer Token).
    Busca tweets recientes con alto engagement sobre los keywords.
    """
    BASE_URL = "https://api.twitter.com/2"

    def __init__(self, settings: Settings): ...

    async def search(self, keywords: list[str], limit: int = 25) -> list[PainSignal]:
        """
        Usa /tweets/search/recent con query combinada de keywords.
        Filtra: lang=es OR lang=en, -is:retweet, min_replies:5.
        Convierte public_metrics.like_count como engagement.
        """

    async def get_trending(self, category: str, limit: int = 10) -> list[PainSignal]:
        """Placeholder — X API v2 no tiene trending público sin acceso premium."""
```

#### ARCHIVO 3: `tools/sources/hackernews_source.py`

```python
class HackerNewsSource:
    """
    Conector HackerNews via API pública (algolia).
    No requiere autenticación. Busca en 'Ask HN' y 'Show HN'.
    """
    BASE_URL = "https://hn.algolia.com/api/v1"

    def __init__(self, scraper: DynamicScraper): ...

    async def search(self, keywords: list[str], limit: int = 25) -> list[PainSignal]:
        """
        Usa /search con tags=ask_hn OR show_hn y query=keywords.
        Engagement = points + num_comments.
        """

    async def get_trending(self, category: str, limit: int = 10) -> list[PainSignal]:
        """Extrae items del feed /topstories filtrados por keywords en título."""
```

**Restricciones**:
- Cada archivo de source NO debe superar **100 líneas**.
- Autenticación siempre desde `Settings` — cero keys hardcodeadas.
- Si la API retorna error 401/403 → lanzar `AgentExecutionError` (credenciales inválidas).
- Usar `httpx.AsyncClient` en todos los conectores. No `praw` (demasiado pesado).

---

### TESTS REQUERIDOS: `tests/tools/sources/`

```python
# reddit_source tests
async def test_reddit_search_returns_pain_signals():      ...  # mock httpx
async def test_reddit_handles_auth_error():               ...  # 401 → AgentExecutionError

# x_source tests
async def test_x_search_filters_retweets():               ...
async def test_x_handles_rate_limit():                    ...  # 429

# hackernews tests
async def test_hn_search_no_auth_required():              ...
async def test_hn_get_trending_filters_by_points():       ...
```

### CHECKLIST DE ENTREGA

- [ ] `tools/sources/__init__.py` con `PainSignal` y `SourceConnector` Protocol
- [ ] Cada source < 100 líneas
- [ ] Cero API keys hardcodeadas
- [ ] `AgentExecutionError` en 401/403
- [ ] 6 tests passing con mocks httpx
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | Cache de datos en `output/scrape_cache/{source}/` via `file_tools` |
| **Hulk** | Cada source < 100L — si crece, extraer helpers |
| **Widow** | `get_trending` en XSource es placeholder — documentarlo, no eliminarlo |
