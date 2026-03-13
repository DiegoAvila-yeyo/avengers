"""tools/sources/hackernews_source.py — Conector HackerNews via Algolia (Prompt #07).

No requiere autenticación. AMD-01 sin I/O de archivos directa.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from tools.sources import PainSignal

_BASE = "https://hn.algolia.com/api/v1"
_FIREBASE = "https://hacker-news.firebaseio.com/v0"


class HackerNewsSource:
    """Conector HackerNews sin autenticación via Algolia API pública."""

    async def search(self, keywords: list[str], limit: int = 25) -> list[PainSignal]:
        """Busca en Ask HN y Show HN por keywords. Engagement = points + comments."""
        query = " ".join(keywords)
        async with httpx.AsyncClient(base_url=_BASE) as client:
            resp = await client.get(
                "/search",
                params={
                    "query": query,
                    "tags": "(ask_hn,show_hn)",
                    "hitsPerPage": limit,
                },
            )
            resp.raise_for_status()
        hits = resp.json().get("hits", [])
        return [_hit_to_signal(h) for h in hits]

    async def get_trending(self, category: str, limit: int = 10) -> list[PainSignal]:
        """Extrae top stories de HN filtrados por score."""
        async with httpx.AsyncClient() as client:
            ids_resp = await client.get(f"{_FIREBASE}/topstories.json")
            ids_resp.raise_for_status()
            top_ids: list[int] = ids_resp.json()[:limit * 3]

            signals: list[PainSignal] = []
            for item_id in top_ids:
                if len(signals) >= limit:
                    break
                item_resp = await client.get(f"{_FIREBASE}/item/{item_id}.json")
                item_resp.raise_for_status()
                item = item_resp.json() or {}
                if item.get("score", 0) > 10:
                    signals.append(_item_to_signal(item))
        return signals


def _hit_to_signal(hit: dict[str, object]) -> PainSignal:
    points = int(hit.get("points") or 0)
    comments = int(hit.get("num_comments") or 0)
    return PainSignal(
        source="hackernews",
        content=str(hit.get("title", "")),
        url=str(hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
        engagement=points + comments,
        author=str(hit.get("author", "")),
        collected_at=datetime.now(tz=timezone.utc),
        keywords=[str(t) for t in (hit.get("_tags") or []) if isinstance(t, str)],
    )


def _item_to_signal(item: dict[str, object]) -> PainSignal:
    return PainSignal(
        source="hackernews",
        content=str(item.get("title", "")),
        url=str(item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}"),
        engagement=int(item.get("score", 0)),
        author=str(item.get("by", "")),
        collected_at=datetime.now(tz=timezone.utc),
        keywords=[str(item.get("type", ""))],
    )
