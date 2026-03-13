"""tests/conftest.py — Fixtures globales para la suite de QA de AVENGERS.

Las variables de entorno se inyectan a nivel de módulo (ANTES de importar core)
para que el singleton `settings` no intente conectarse a APIs reales.

Garantías:
- Nunca toca la BD de producción  (DATABASE_URL termina en _test).
- Nunca llama APIs reales          (credenciales son valores falsos de prueba).
- asyncio_mode = "auto"            (configurado en pyproject.toml).
"""

from __future__ import annotations

import os
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Inyección de env vars ANTES de cualquier import de core ─────────────────
os.environ.setdefault("OPENAI_API_KEY", "sk-test-openai-key-for-tests")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-anthropic-key-for-tests")
os.environ.setdefault("REDDIT_CLIENT_ID", "test-reddit-id-abc123")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "test-reddit-secret-abc123")
os.environ.setdefault("X_API_KEY", "test-x-api-key-abc123")
os.environ.setdefault("X_API_SECRET", "test-x-api-secret-abc123")
# AMD-01 SAFETY: sufijo _test garantiza aislamiento de la BD de producción.
os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017/avengers_test")

# Los imports de core van DESPUÉS de configurar el entorno.
from core.llm_client import LLMClient  # noqa: E402
from core.repository import MissionRepository  # noqa: E402
from core.settings import Settings  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def settings() -> Settings:
    """Settings instanciado con valores de prueba (sin credenciales reales)."""
    return Settings()


@pytest.fixture
def llm_client() -> LLMClient:
    """LLMClient con transportes HTTP mockeados: cero llamadas reales a la API."""
    client = LLMClient()
    client._openai = MagicMock()
    client._anthropic = MagicMock()
    return client


@pytest.fixture
def mission_repo() -> Generator[MissionRepository, None, None]:
    """MissionRepository aislado: BD mockeada — nunca toca avengers ni avengers_test."""
    mock_col = AsyncMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_col

    with patch("core.repository.db_manager") as mock_dbm:
        mock_dbm.get_database.return_value = mock_db
        yield MissionRepository()
