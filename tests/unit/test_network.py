"""tests/unit/test_network.py — AMD-02 Retry Logic: validación de resiliencia LLM.

Verifica que LLMClient reintenta exactamente _RETRY_ATTEMPTS veces ante errores
de servidor (500) antes de propagar la excepción, usando mocks sin llamadas reales.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm_client import (
    AgentRole,
    LLMClient,
    LLMRequest,
    _RETRY_ATTEMPTS,
)


# ── Fixture local: cliente con transporte mockeado ────────────────────────────


@pytest.fixture
def mock_client() -> LLMClient:
    """LLMClient con backends HTTP mockeados. No realiza ninguna llamada real."""
    client = LLMClient.__new__(LLMClient)
    client._openai = MagicMock()
    client._anthropic = MagicMock()
    return client


def _make_request(role: AgentRole) -> LLMRequest:
    return LLMRequest(role=role, system_prompt="sys", user_message="msg")


# ── OpenAI (roles: NICK_FURY, THOR, CAPTAIN_AMERICA) ─────────────────────────


async def test_openai_retries_exactly_n_times_on_failure(mock_client: LLMClient) -> None:
    """Ante N fallos consecutivos, se debe reintentar exactamente _RETRY_ATTEMPTS veces."""
    mock_create = AsyncMock(side_effect=RuntimeError("Simulated 500"))
    mock_client._openai.chat.completions.create = mock_create

    with patch("asyncio.sleep"):
        with pytest.raises(RuntimeError, match="500"):
            await mock_client._complete_openai(_make_request(AgentRole.NICK_FURY))

    assert mock_create.call_count == _RETRY_ATTEMPTS, (
        f"Se esperaban {_RETRY_ATTEMPTS} intentos, se hicieron {mock_create.call_count}"
    )


async def test_openai_succeeds_after_partial_failures(mock_client: LLMClient) -> None:
    """El cliente debe recuperarse y retornar éxito si un reintento tiene éxito."""
    success = MagicMock()
    success.choices = [MagicMock()]
    success.choices[0].message.content = "Avengers assemble!"
    success.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

    mock_client._openai.chat.completions.create = AsyncMock(
        side_effect=[RuntimeError("500"), RuntimeError("500"), success]
    )

    with patch("asyncio.sleep"):
        response = await mock_client._complete_openai(_make_request(AgentRole.THOR))

    assert response.content == "Avengers assemble!"
    assert mock_client._openai.chat.completions.create.call_count == 3


# ── Anthropic / Claude (roles: IRON_CODER, BLACK_WIDOW, INFILTRADO) ──────────


async def test_anthropic_retries_exactly_n_times_on_failure(mock_client: LLMClient) -> None:
    """Ante N fallos consecutivos, se debe reintentar exactamente _RETRY_ATTEMPTS veces."""
    mock_create = AsyncMock(side_effect=RuntimeError("Simulated 500"))
    mock_client._anthropic.messages.create = mock_create

    with patch("asyncio.sleep"):
        with pytest.raises(RuntimeError, match="500"):
            await mock_client._complete_anthropic(_make_request(AgentRole.IRON_CODER))

    assert mock_create.call_count == _RETRY_ATTEMPTS, (
        f"Se esperaban {_RETRY_ATTEMPTS} intentos, se hicieron {mock_create.call_count}"
    )


async def test_anthropic_succeeds_after_partial_failures(mock_client: LLMClient) -> None:
    """El cliente Claude debe recuperarse si un reintento tiene éxito."""
    success = MagicMock()
    success.content = [MagicMock(text="Iron Coder ready.")]
    success.usage = MagicMock(input_tokens=8, output_tokens=4)

    mock_client._anthropic.messages.create = AsyncMock(
        side_effect=[RuntimeError("500"), success]
    )

    with patch("asyncio.sleep"):
        response = await mock_client._complete_anthropic(_make_request(AgentRole.BLACK_WIDOW))

    assert response.content == "Iron Coder ready."
    assert mock_client._anthropic.messages.create.call_count == 2


async def test_retry_count_matches_configured_attempts(mock_client: LLMClient) -> None:
    """El número de reintentos debe ser exactamente el definido en _RETRY_ATTEMPTS."""
    assert _RETRY_ATTEMPTS == 4, (
        "AMD-02 define 4 intentos (1 inicial + 3 reintentos). "
        "Si cambias _RETRY_ATTEMPTS, actualiza este test."
    )
