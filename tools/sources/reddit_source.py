"""tools/sources/reddit_source.py — Conector Reddit via OAuth2 (Prompt #07).

AMD-01: sin I/O de archivos directa — el caché lo gestiona DynamicScraper.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone

import httpx

from core.exceptions import AgentExecutionError
from core.models import AgentRole
from core.settings import Settings
from tools.sources import PainSignal

_BASE = "https://oauth.reddit.com"
_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_SUBREDDITS: dict[str, list[str]] = {
    "default": ["entrepreneur", "startups", "SaaS", "webdev"],
}


class RedditSource:
    """Conector Reddit via API OAuth2. Busca posts con alto engagement."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._token: str | None = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        client_id = self._settings.reddit_client_id.get_secret_value()
        secret = self._settings.reddit_client_secret.get_secret_value()
        creds = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TOKEN_URL,
                headers={"Authorization": f"Basic {creds}"},
                data={"grant_type": "client_credentials"},
                auth=None,
            )
            if resp.status_code in (401, 403):
                raise AgentExecutionError(AgentRole.THOR, "Reddit auth failed", attempt=1)
            resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    async def search(self, keywords: list[str], limit: int = 25) -> list[PainSignal]:
        """Busca posts usando /search.json. sort=top, t=month."""
        token = await self._get_token()
        query = " OR ".join(keywords)
        async with httpx.AsyncClient(base_url=_BASE) as client:
            resp = await client.get(
                "/search.json",
                params={"q": query, "sort": "top", "t": "month", "limit": limit},
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code in (401, 403):
                raise AgentExecutionError(AgentRole.THOR, "Reddit search auth error", attempt=1)
            resp.raise_for_status()
        posts = resp.json().get("data", {}).get("children", [])
        return [_post_to_signal(p["data"]) for p in posts]

    async def get_trending(self, category: str, limit: int = 10) -> list[PainSignal]:
        """Extrae posts trending de subreddits predefinidos por categoría."""
        token = await self._get_token()
        subs = _SUBREDDITS.get(category, _SUBREDDITS["default"])
        signals: list[PainSignal] = []
        async with httpx.AsyncClient(base_url=_BASE) as client:
            for sub in subs:
                resp = await client.get(
                    f"/r/{sub}/hot.json",
                    params={"limit": limit},
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code in (401, 403):
                    raise AgentExecutionError(
                        AgentRole.THOR, f"Reddit /r/{sub} auth error", attempt=1
                    )
                resp.raise_for_status()
                posts = resp.json().get("data", {}).get("children", [])
                signals.extend(_post_to_signal(p["data"]) for p in posts)
        return signals[:limit]


def _post_to_signal(post: dict[str, object]) -> PainSignal:
    return PainSignal(
        source="reddit",
        content=str(post.get("title", "")) + " " + str(post.get("selftext", "")),
        url=f"https://reddit.com{post.get('permalink', '')}",
        engagement=int(post.get("score", 0)),
        author=str(post.get("author", "")),
        collected_at=datetime.now(tz=timezone.utc),
        keywords=list(filter(None, [post.get("link_flair_text")])),
    )
