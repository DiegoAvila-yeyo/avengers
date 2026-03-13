"""tests/tools/sources/test_hackernews_source.py — Tests del conector HackerNews."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.sources.hackernews_source import HackerNewsSource

_SEARCH_RESP = {
    "hits": [
        {
            "title": "Ask HN: Why does X suck?",
            "url": "https://news.ycombinator.com/item?id=1",
            "points": 120,
            "num_comments": 45,
            "author": "hn_user",
            "objectID": "1",
            "_tags": ["ask_hn", "story"],
        }
    ]
}


def _mock_response(status: int, json_data: object) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.asyncio
async def test_hn_search_no_auth_required() -> None:
    """HackerNews no requiere token — verifica que no se envíe Authorization."""
    source = HackerNewsSource()

    with patch("tools.sources.hackernews_source.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_cm.get = AsyncMock(return_value=_mock_response(200, _SEARCH_RESP))
        mock_client_cls.return_value = mock_cm

        signals = await source.search(["suck", "broken"], limit=5)
        _, kwargs = mock_cm.get.call_args
        headers = kwargs.get("headers", {})

    assert "Authorization" not in headers
    assert len(signals) == 1
    assert signals[0].engagement == 165  # 120 + 45


@pytest.mark.asyncio
async def test_hn_get_trending_filters_by_points() -> None:
    """get_trending solo incluye items con score > 10."""
    source = HackerNewsSource()

    top_ids = [1, 2]
    item_high = {"id": 1, "title": "High score", "score": 50, "by": "usr", "type": "story"}
    item_low = {"id": 2, "title": "Low score", "score": 5, "by": "usr", "type": "story"}

    responses = [
        _mock_response(200, top_ids),
        _mock_response(200, item_high),
        _mock_response(200, item_low),
    ]

    with patch("tools.sources.hackernews_source.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_cm.get = AsyncMock(side_effect=responses)
        mock_client_cls.return_value = mock_cm

        signals = await source.get_trending("default", limit=10)

    assert len(signals) == 1
    assert signals[0].engagement == 50
