"""core/settings.py — Configuración global con Pydantic v2.

Carga variables de entorno desde .env (si existe) y valida tipos en runtime.
Usar siempre la instancia singleton `settings` importada desde este módulo.

    from core.settings import settings
"""

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la Factoría AVENGERS.

    Todas las API Keys se manejan como SecretStr para evitar leaks en logs.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Providers ──────────────────────────────────────────────────────
    openai_api_key: SecretStr = Field(
        ...,
        description="API Key de OpenAI (requerida).",
    )
    anthropic_api_key: SecretStr = Field(
        ...,
        description="API Key de Anthropic (requerida).",
    )

    # ── Social / Data Sources ───────────────────────────────────────────────
    reddit_client_id: SecretStr = Field(
        ...,
        description="Client ID de la app Reddit (OAuth2).",
    )
    reddit_client_secret: SecretStr = Field(
        ...,
        description="Client Secret de la app Reddit (OAuth2).",
    )
    x_api_key: SecretStr = Field(
        ...,
        description="API Key de X/Twitter (Bearer o v2).",
    )
    x_api_secret: SecretStr = Field(
        ...,
        description="API Secret de X/Twitter.",
    )

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="mongodb://localhost:27017/avengers",
        description="URL de conexión a la base de datos (MongoDB o PostgreSQL).",
    )

    # ── App Config ──────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Entorno de ejecución.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Nivel de logging.",
    )
    max_context_lines: int = Field(
        default=300,
        ge=50,
        le=500,
        description="Límite de líneas de contexto inyectadas a cada agente (Protocolo Hulk).",
    )

    # ── Validadores ─────────────────────────────────────────────────────────
    @field_validator("openai_api_key", "anthropic_api_key", mode="before")
    @classmethod
    def _validate_llm_key(cls, v: object) -> object:
        """Rechaza placeholders evidentes como 'sk-...' o cadenas vacías."""
        raw = v.get_secret_value() if hasattr(v, "get_secret_value") else str(v)
        if not raw or raw.strip() in {"sk-...", "sk-ant-..."}:
            raise ValueError(
                "API Key de LLM no configurada. Revisa tu archivo .env."
            )
        return v

    @field_validator("x_api_key", "x_api_secret", "reddit_client_id", "reddit_client_secret", mode="before")
    @classmethod
    def _validate_social_key(cls, v: object) -> object:
        """Rechaza valores placeholder de las claves sociales."""
        raw = v.get_secret_value() if hasattr(v, "get_secret_value") else str(v)
        placeholder_prefixes = ("your_", "change_me", "")
        if not raw or any(raw.strip().startswith(p) for p in placeholder_prefixes if p):
            raise ValueError(
                "Clave de API social no configurada. Revisa tu archivo .env."
            )
        return v


# Singleton — importar directamente en lugar de instanciar Settings() en cada módulo.
settings = Settings()
