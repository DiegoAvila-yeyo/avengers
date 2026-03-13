"""tests/tools/sources/test_x_source.py — Tests del conector X/Twitter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from core.exceptions import AgentExecutionError
from core.settings import Settings
from tools.sources.x_source import XSource

_SEARCH_RESP = {
    "data": [
        {
            "id": "123",
            "text": "This tool is broken and painful",
            "author_id": "u1",
            "public_metrics": {"like_count": 42, "reply_count": 5},
        }
    ],
    "includes": {"users": [{"id": "u1", "username": "dev_user"}]},
}


def _make_settings() -> Settings:
    s = MagicMock(spec=Settings)
    s.x_api_key = SecretStr("mock_bearer_token")
    return s


def _mock_response(status: int, json_data: dict) -> MagicMock:  # type: ignore[type-arg]
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.asyncio
async def test_x_search_filters_retweets() -> None:
    """Verifica que la query incluye -is:retweet."""
    source = XSource(_make_settings())

    with patch("tools.sources.x_source.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_cm.get = AsyncMock(return_value=_mock_response(200, _SEARCH_RESP))
        mock_client_cls.return_value = mock_cm

        signals = await source.search(["broken"], limit=10)
        _, kwargs = mock_cm.get.call_args
        query = kwargs["params"]["query"]

    assert "-is:retweet" in query
    assert len(signals) == 1
    assert signals[0].author == "dev_user"


@pytest.mark.asyncio
async def test_x_handles_rate_limit() -> None:
    source = XSource(_make_settings())

    with patch("tools.sources.x_source.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_cm.get = AsyncMock(return_value=_mock_response(429, {}))
        mock_client_cls.return_value = mock_cm

        with pytest.raises(AgentExecutionError, match="rate limit"):
            await source.search(["test"], limit=5)
