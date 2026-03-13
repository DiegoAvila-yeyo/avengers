"""tests/tools/sources/test_reddit_source.py — Tests del conector Reddit."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from core.exceptions import AgentExecutionError
from core.settings import Settings
from tools.sources.reddit_source import RedditSource

_TOKEN_RESP = {"access_token": "mock_token", "expires_in": 3600}
_SEARCH_RESP = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "Pain point SaaS",
                    "selftext": "We struggle with X",
                    "permalink": "/r/saas/comments/abc",
                    "score": 150,
                    "author": "user1",
                    "link_flair_text": "SaaS",
                }
            }
        ]
    }
}


def _make_settings() -> Settings:
    s = MagicMock(spec=Settings)
    s.reddit_client_id = SecretStr("mock_id")
    s.reddit_client_secret = SecretStr("mock_secret")
    return s


def _mock_response(status: int, json_data: dict) -> MagicMock:  # type: ignore[type-arg]
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.asyncio
async def test_reddit_search_returns_pain_signals() -> None:
    source = RedditSource(_make_settings())
    source._token = "mock_token"

    with patch("tools.sources.reddit_source.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_cm.get = AsyncMock(return_value=_mock_response(200, _SEARCH_RESP))
        mock_client_cls.return_value = mock_cm

        signals = await source.search(["SaaS", "pain"], limit=5)

    assert len(signals) == 1
    assert signals[0].source == "reddit"
    assert signals[0].engagement == 150
    assert "SaaS" in signals[0].keywords


@pytest.mark.asyncio
async def test_reddit_handles_auth_error() -> None:
    source = RedditSource(_make_settings())

    with patch("tools.sources.reddit_source.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_cm.post = AsyncMock(return_value=_mock_response(401, {}))
        mock_client_cls.return_value = mock_cm

        with pytest.raises(AgentExecutionError):
            await source.search(["test"], limit=5)
