# Prompt #01 — Config Global: pydantic-settings, .env, Constantes del Sistema

**Fase**: 1 — Sistema Nervioso Central
**Agente objetivo**: Core
**Archivo(s) a crear**:
- `core/settings.py` — Configuración global via pydantic-settings
- `core/constants.py` — Constantes inmutables del sistema
**Dependencias previas**: Ninguna — este es el punto de partida absoluto
**Checkpoint humano**: No

### 🔒 Enmienda AMD-05 Persistencia Estricta
Las credenciales de base de datos se leen **únicamente** desde `Settings`.
Ningún otro módulo importa variables de entorno directamente.

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en configuración de aplicaciones
y seguridad de credenciales, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → stack tecnológico y variables de entorno.
3. Lee `.env.example` → todas las variables disponibles.

---

### TAREA: Crear la configuración base del sistema

#### ARCHIVO 1: `core/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyUrl, field_validator
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    app_env: str = Field(default="development", pattern="^(development|staging|production)$")
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    max_context_lines: int = Field(default=300, ge=100, le=300)
    project_root: str = Field(default=".")  # Ruta raíz — ROOT JAIL usa este valor

    # ── LLMs ─────────────────────────────────────────────────
    openai_api_key: str = Field(default="", repr=False)
    anthropic_api_key: str = Field(default="", repr=False)
    default_llm_provider: str = Field(default="openai", pattern="^(openai|anthropic)$")
    llm_max_tokens: int = Field(default=4096, ge=256, le=32768)

    # ── Database ─────────────────────────────────────────────
    database_url: str = Field(default="mongodb://localhost:27017/avengers", repr=False)
    db_name: str = "avengers"
    db_missions_collection: str = "missions"
    db_checkpoints_collection: str = "checkpoints"

    # ── Social APIs ──────────────────────────────────────────
    reddit_client_id: str = Field(default="", repr=False)
    reddit_client_secret: str = Field(default="", repr=False)
    x_api_key: str = Field(default="", repr=False)
    x_api_secret: str = Field(default="", repr=False)

    # ── Agent Limits ─────────────────────────────────────────
    state_log_max_entries: int = Field(default=50, ge=10, le=200)
    retry_max_attempts: int = Field(default=3, ge=1, le=5)
    retry_base_delay: float = Field(default=2.0, gt=0.0)

    @field_validator("openai_api_key", "anthropic_api_key", mode="before")
    @classmethod
    def mask_sensitive(cls, v: str) -> str:
        # Validación: si está en producción y está vacío → error
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton de settings. Usar siempre esta función, nunca instanciar Settings()."""
    return Settings()
```

**Restricciones**:
- `get_settings()` es la única forma de obtener la configuración. Nunca `Settings()` directo.
- `repr=False` en TODOS los campos de credenciales para evitar leakage en logs.
- **Este archivo NO debe superar 80 líneas.**

---

#### ARCHIVO 2: `core/constants.py`

```python
from typing import Final

# ── Límites del Sistema ───────────────────────────────────────────
MAX_FILE_LINES: Final[int] = 300          # Protocolo Hulk
STATE_LOG_TTL: Final[int] = 50            # Entradas máximas en State Log
MAX_INTERNAL_RETRIES: Final[int] = 2      # Reintentos internos de un agente (LLM parse)
FURY_MAX_RETRIES: Final[int] = 3          # Reintentos de Nick Fury por agente
FURY_BASE_DELAY: Final[float] = 2.0       # Segundos — backoff exponencial

# ── Paths Relativos ───────────────────────────────────────────────
MISSIONS_DIR: Final[str] = "missions"
BLUEPRINTS_DIR: Final[str] = "blueprints"
OUTPUT_DIR: Final[str] = "output"
CONNECTORS_DIR: Final[str] = "tools/connectors"

# ── Colecciones MongoDB ───────────────────────────────────────────
COL_MISSIONS: Final[str] = "missions"
COL_CHECKPOINTS: Final[str] = "checkpoints"
COL_BRIEFS: Final[str] = "briefs"

# ── LLM ──────────────────────────────────────────────────────────
LLM_TEMPERATURE: Final[float] = 0.2      # Baja para outputs estructurados
LLM_JSON_MODE: Final[bool] = True
```

**Restricciones**:
- Usar `typing.Final` en todas las constantes.
- Ninguna constante puede ser mutable (no `list`, no `dict` como constante).
- **Este archivo NO debe superar 50 líneas.**

---

### TESTS REQUERIDOS: `tests/core/test_settings.py`

```python
# Test 1: Settings carga desde .env.example sin errores
def test_settings_load_from_env(): ...

# Test 2: get_settings() retorna el mismo singleton (lru_cache)
def test_get_settings_is_singleton(): ...

# Test 3: app_env con valor inválido → ValidationError
def test_invalid_app_env_raises(): ...

# Test 4: Credenciales tienen repr=False (no aparecen en str(settings))
def test_credentials_not_in_repr(): ...

# Test 5: max_context_lines no puede superar 300 (Protocolo Hulk en config)
def test_max_context_lines_capped_at_300(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `core/settings.py` < 80 líneas, `repr=False` en credenciales
- [ ] `core/constants.py` < 50 líneas, todas con `Final`
- [ ] `get_settings()` como singleton via `lru_cache`
- [ ] 5 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Hulk** (> 300L) | `max_context_lines` ≤ 300 enforced en schema |
| **Widow** | Cero imports sin usar |
| **Seguridad** | `repr=False` en TODOS los campos de API keys |
