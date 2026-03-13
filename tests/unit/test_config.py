"""tests/unit/test_config.py — Validación de la configuración Pydantic.

Verifica que:
  1. Las API Keys son SecretStr (no se filtran en repr/str/logs).
  2. Settings lanza ValidationError si faltan variables críticas.
  3. La BD de tests usa el sufijo _test (nunca producción).
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError
from pydantic_settings import SettingsConfigDict

from core.settings import Settings


# ── Subclase de Settings con env_file=None para aislamiento total ─────────────
class _IsolatedSettings(Settings):
    """Settings sin lectura de archivo .env — sólo env vars inyectadas."""

    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )


# ── Caso 1: API Keys son SecretStr ────────────────────────────────────────────


def test_openai_key_is_secret_str(settings: Settings) -> None:
    """openai_api_key debe ser de tipo SecretStr."""
    assert isinstance(settings.openai_api_key, SecretStr)


def test_anthropic_key_is_secret_str(settings: Settings) -> None:
    """anthropic_api_key debe ser de tipo SecretStr."""
    assert isinstance(settings.anthropic_api_key, SecretStr)


def test_openai_key_repr_does_not_leak_value(settings: Settings) -> None:
    """repr(openai_api_key) no debe exponer el valor real de la key."""
    raw = settings.openai_api_key.get_secret_value()
    key_repr = repr(settings.openai_api_key)
    assert raw not in key_repr, "¡El valor real de la API Key está visible en repr!"


def test_openai_key_str_does_not_leak_value(settings: Settings) -> None:
    """str(openai_api_key) no debe exponer el valor real de la key."""
    raw = settings.openai_api_key.get_secret_value()
    key_str = str(settings.openai_api_key)
    assert raw not in key_str, "¡El valor real de la API Key está visible en str!"


def test_anthropic_key_repr_does_not_leak_value(settings: Settings) -> None:
    """repr(anthropic_api_key) no debe exponer el valor real."""
    raw = settings.anthropic_api_key.get_secret_value()
    assert raw not in repr(settings.anthropic_api_key)


# ── Caso 2: Faltan variables críticas → ValidationError ──────────────────────


def test_missing_openai_key_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """La ausencia de OPENAI_API_KEY debe lanzar ValidationError."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValidationError, match="openai_api_key"):
        _IsolatedSettings()


def test_missing_anthropic_key_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """La ausencia de ANTHROPIC_API_KEY debe lanzar ValidationError."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValidationError, match="anthropic_api_key"):
        _IsolatedSettings()


def test_placeholder_openai_key_raises_validation_error() -> None:
    """Un valor placeholder 'sk-...' debe ser rechazado por el validador."""
    with pytest.raises(ValidationError):
        _IsolatedSettings(openai_api_key="sk-...")  # type: ignore[call-arg]


# ── Caso 3: Garantía de aislamiento de BD ────────────────────────────────────


def test_database_url_uses_test_suffix(settings: Settings) -> None:
    """La DATABASE_URL en tests debe apuntar a una BD con sufijo _test."""
    assert "test" in settings.database_url.lower(), (
        f"La BD de tests no usa sufijo _test: {settings.database_url!r}"
    )
