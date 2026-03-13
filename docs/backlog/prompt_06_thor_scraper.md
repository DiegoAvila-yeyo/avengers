# Prompt #06 — Thor: Motor de Scraping Dinámico

**Fase**: 2 — Equipo de Estrategia
**Agente objetivo**: Thor
**Archivo(s) a crear**:
- `tools/scraper.py` — Motor de scraping async con httpx + parser HTML
**Dependencias previas**: Prompt #01 (Settings), Prompt #11 (file_tools — ROOT JAIL)
**Checkpoint humano**: No

### 🔒 Enmienda AMD-01 Root Jail
Los archivos descargados o cacheados por el scraper se guardan ÚNICAMENTE en
`output/scrape_cache/` dentro del project_root, usando `file_tools.write_file()`.
Nunca se escriben archivos en rutas externas al proyecto.

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en web scraping async y extracción
de datos, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → rol de Thor como Trend-Hunter.
3. Lee `core/settings.py` → timeouts, user agents.
4. Lee `tools/file_tools.py` → `write_file`, `resolve_safe_path` (ROOT JAIL).

---

### TAREA: Crear el motor de scraping de Thor

#### ARCHIVO: `tools/scraper.py`

```python
class ScrapedPage(BaseModel):
    """Resultado normalizado de una página scrapeada."""
    url: str
    title: str
    raw_text: str           # Texto plano extraído (sin HTML)
    links: list[str]        # URLs encontradas en la página
    scraped_at: datetime
    status_code: int
    source_type: str        # "forum" | "reddit" | "x" | "news" | "docs"


class ScraperConfig(BaseModel):
    """Configuración del scraper, inyectada desde Settings."""
    timeout_seconds: int = 15
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent: str = "Mozilla/5.0 (AVENGERS-Bot/1.0)"
    respect_robots_txt: bool = True
    max_content_length_bytes: int = 500_000   # 500KB máx por página


class DynamicScraper:
    """
    Motor de scraping async. Usa httpx con reintentos y manejo de errores.
    Thor lo usa como herramienta principal de investigación.
    No guarda estado entre llamadas — stateless.
    """

    def __init__(self, config: ScraperConfig, file_tools: FileTools): ...

    async def fetch(self, url: str) -> ScrapedPage:
        """
        Descarga y parsea una URL.
        - Reintentos: hasta config.max_retries con delay exponencial.
        - Si status_code == 429 (rate limit) → esperar Retry-After header.
        - Si content > max_content_length_bytes → truncar con aviso en logs.
        - Extrae texto plano con BeautifulSoup (lxml parser).
        - Lanza ScraperError si falla tras todos los reintentos.
        """

    async def fetch_many(self, urls: list[str], concurrency: int = 5) -> list[ScrapedPage]:
        """
        Descarga múltiples URLs en paralelo con semáforo de concurrencia.
        Retorna lista de ScrapedPage (los fallidos incluyen error en raw_text).
        """

    async def cache_result(self, page: ScrapedPage, mission_id: str) -> str:
        """
        Guarda el resultado en output/scrape_cache/{mission_id}/{url_hash}.json
        usando file_tools.write_file(). [ROOT JAIL activo]
        Retorna la ruta relativa del archivo guardado.
        """

    def extract_text(self, html: str) -> str:
        """
        Extrae texto limpio desde HTML.
        - Elimina scripts, styles, navegación, footers.
        - Colapsa espacios en blanco.
        - Retorna máximo 10.000 chars (contexto LLM).
        """
```

**Restricciones**:
- Usar `httpx.AsyncClient` con `follow_redirects=True` y `timeout=config.timeout_seconds`.
- NO usar `requests`, `selenium` ni `playwright` — httpx puro.
- BeautifulSoup solo para parsing HTML; no lógica de negocio en el parser.
- **Este archivo NO debe superar 150 líneas.**

---

### TESTS REQUERIDOS: `tests/tools/test_scraper.py`

```python
# Test 1: fetch() retorna ScrapedPage con texto extraído (mock httpx)
async def test_fetch_returns_scraped_page(): ...

# Test 2: fetch() reintenta en error 500 (max_retries=3)
async def test_fetch_retries_on_server_error(): ...

# Test 3: fetch() maneja rate limit 429 con Retry-After
async def test_fetch_handles_rate_limit(): ...

# Test 4: fetch_many() respeta límite de concurrencia
async def test_fetch_many_respects_concurrency(): ...

# Test 5: cache_result() escribe en output/ (ROOT JAIL)
async def test_cache_result_writes_inside_output(): ...

# Test 6: extract_text() elimina scripts y colapsa whitespace
def test_extract_text_cleans_html(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `tools/scraper.py` < 150 líneas
- [ ] Reintentos con backoff exponencial en `fetch()`
- [ ] `cache_result()` via `file_tools` — ROOT JAIL activo
- [ ] `extract_text()` limpia scripts y acota a 10.000 chars
- [ ] 6 tests passing con mocks httpx
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | Cache solo en `output/scrape_cache/` via `file_tools` |
| **Hulk** (> 300L) | DETENTE, modulariza |
| **Widow** | Sin código de scraping muerto ni parsers duplicados |
