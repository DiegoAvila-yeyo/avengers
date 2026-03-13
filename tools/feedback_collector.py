"""tools/feedback_collector.py — Colector de comentarios post-publicación (Prompt #23)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel

from tools.sources import PainSignal

if TYPE_CHECKING:
    from agents.infiltrado import SocialPost
    from tools.sources.reddit_source import RedditSource
    from tools.sources.x_source import XSource

logger = logging.getLogger(__name__)


class FeedbackItem(BaseModel):
    """Un comentario/respuesta real de un usuario al post publicado."""

    source: str
    post_url: str
    content: str
    author: str
    sentiment: str | None = None
    is_feature_request: bool = False
    is_bug_report: bool = False
    engagement: int
    collected_at: datetime


class FeedbackSummary(BaseModel):
    """Resumen del ciclo de feedback de una misión."""

    mission_id: str
    total_items: int
    positive_ratio: float
    feature_requests: list[str]
    pain_points: list[str]
    suggested_keyword: str
    generated_at: datetime


class FeedbackCollector:
    """Recoge comentarios de posts publicados y extrae insights para Thor.

    Opera 24-48h después de la publicación (llamado por Nick Fury en el loop closure).
    Para el análisis LLM, usar FeedbackAnalyzer en tools/feedback_analyzer.py.
    """

    def __init__(
        self,
        x_source: XSource,
        reddit_source: RedditSource,
    ) -> None:
        self._x = x_source
        self._reddit = reddit_source

    async def collect(
        self, posts: list[SocialPost], hours_window: int = 48
    ) -> list[FeedbackItem]:
        """Recoge comentarios de X y Reddit para los posts publicados."""
        items: list[FeedbackItem] = []
        for post in posts:
            if not post.post_url:
                continue
            if post.platform == "x":
                items.extend(await self._collect_x_replies(post))
            elif post.platform == "reddit":
                items.extend(await self._collect_reddit_comments(post))
        return items

    async def to_pain_signals(self, summary: FeedbackSummary) -> list[PainSignal]:
        """Convierte FeedbackSummary en PainSignals para que Thor los use como semilla."""
        now = datetime.now(tz=timezone.utc)  # noqa: UP017
        return [
            PainSignal(
                source="feedback_loop",
                content=text,
                url=f"avengers://missions/{summary.mission_id}/feedback",
                engagement=1,
                author="feedback_collector",
                collected_at=now,
                keywords=[summary.suggested_keyword],
            )
            for text in summary.feature_requests + summary.pain_points
        ]

    async def _collect_x_replies(self, post: SocialPost) -> list[FeedbackItem]:
        tweet_id = (post.post_url or "").rstrip("/").rsplit("/", 1)[-1]
        token = self._x._settings.x_api_key.get_secret_value()
        try:
            async with httpx.AsyncClient(base_url="https://api.twitter.com/2") as client:
                resp = await client.get(
                    "/tweets/search/recent",
                    params={"query": f"conversation_id:{tweet_id} -is:retweet",
                            "tweet.fields": "public_metrics,author_id"},
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp.raise_for_status()
                return [
                    FeedbackItem(
                        source="x", post_url=post.post_url or "",
                        content=t.get("text", ""), author=t.get("author_id", ""),
                        engagement=t.get("public_metrics", {}).get("like_count", 0),
                        collected_at=datetime.now(tz=timezone.utc),  # noqa: UP017
                    )
                    for t in resp.json().get("data") or []
                ]
        except Exception as exc:
            logger.warning("X replies fetch failed for %s: %s", post.post_url, exc)
        return []

    async def _collect_reddit_comments(self, post: SocialPost) -> list[FeedbackItem]:
        parts = (post.post_url or "").split("/")
        try:
            post_id = parts[parts.index("comments") + 1]
            sub = parts[parts.index("r") + 1]
        except (ValueError, IndexError):
            return []
        token = await self._reddit._get_token()
        try:
            async with httpx.AsyncClient(base_url="https://oauth.reddit.com") as client:
                resp = await client.get(
                    f"/r/{sub}/comments/{post_id}.json",
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp.raise_for_status()
                data = resp.json()
                children = data[1]["data"]["children"] if len(data) > 1 else []
                return [
                    FeedbackItem(
                        source="reddit", post_url=post.post_url or "",
                        content=c.get("data", {}).get("body", ""),
                        author=c.get("data", {}).get("author", ""),
                        engagement=c.get("data", {}).get("ups", 0),
                        collected_at=datetime.now(tz=timezone.utc),  # noqa: UP017
                    )
                    for c in children
                ]
        except Exception as exc:
            logger.warning("Reddit comments fetch failed for %s: %s", post.post_url, exc)
        return []
