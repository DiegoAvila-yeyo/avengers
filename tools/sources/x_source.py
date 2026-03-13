"""tools/sources/x_source.py — Conector X/Twitter API v2 (Prompt #07).

AMD-01: sin I/O de archivos directa.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from core.exceptions import AgentExecutionError
from core.models import AgentRole
from core.settings import Settings
from tools.sources import PainSignal

_BASE = "https://api.twitter.com/2"


class XSource:
    """Conector X/Twitter API v2 (Bearer Token). Busca tweets con engagement."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def _headers(self) -> dict[str, str]:
        token = self._settings.x_api_key.get_secret_value()
        return {"Authorization": f"Bearer {token}"}

    async def search(self, keywords: list[str], limit: int = 25) -> list[PainSignal]:
        """Busca tweets recientes filtrando retweets y con mínimo engagement."""
        query = " OR ".join(f'"{kw}"' for kw in keywords)
        query += " -is:retweet lang:en min_replies:5"
        async with httpx.AsyncClient(base_url=_BASE) as client:
            resp = await client.get(
                "/tweets/search/recent",
                params={
                    "query": query,
                    "max_results": min(limit, 100),
                    "tweet.fields": "public_metrics,author_id,created_at",
                    "expansions": "author_id",
                    "user.fields": "username",
                },
                headers=self._headers,
            )
            if resp.status_code == 429:
                raise AgentExecutionError(AgentRole.THOR, "X API rate limit exceeded", attempt=1)
            if resp.status_code in (401, 403):
                raise AgentExecutionError(AgentRole.THOR, "X API auth error", attempt=1)
            resp.raise_for_status()
        data = resp.json()
        tweets = data.get("data") or []
        users = {u["id"]: u["username"] for u in (data.get("includes") or {}).get("users", [])}
        return [_tweet_to_signal(t, users) for t in tweets]

    async def get_trending(self, category: str, limit: int = 10) -> list[PainSignal]:
        """Placeholder — X API v2 no expone trending sin acceso premium."""
        # Trending topics requieren acceso v1.1 o suscripción premium.
        # Retorna lista vacía de forma deliberada; no es un bug.
        return []


def _tweet_to_signal(tweet: dict[str, object], users: dict[str, str]) -> PainSignal:
    metrics: dict[str, int] = tweet.get("public_metrics", {})  # type: ignore[assignment]
    author_id = str(tweet.get("author_id", ""))
    return PainSignal(
        source="x",
        content=str(tweet.get("text", "")),
        url=f"https://twitter.com/i/web/status/{tweet.get('id', '')}",
        engagement=metrics.get("like_count", 0),
        author=users.get(author_id, author_id),
        collected_at=datetime.now(tz=timezone.utc),
        keywords=[],
    )
