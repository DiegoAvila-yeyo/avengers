"""agents/infiltrado.py — El Infiltrado: Growth Agent (Fase 5).

ROOT JAIL: todo I/O via tools.file_tools. Checkpoint humano OBLIGATORIO.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, ClassVar

import httpx
import yaml
from pydantic import BaseModel

from core.models import AgentRole, LogEntry, Mission
from tools.file_tools import read_file, write_file

if TYPE_CHECKING:
    from core.checkpoints import CheckpointManager
    from core.llm_client import LLMClient
    from tools.sources.reddit_source import RedditSource
    from tools.sources.x_source import XSource

logger = logging.getLogger(__name__)


class SocialPost(BaseModel):
    platform: str
    content: str
    subreddit: str | None = None
    thread_title: str | None = None
    approved: bool = False
    published_at: datetime | None = None
    post_url: str | None = None


class InfiltradoAgent:
    """Growth agent: genera contenido social, aguarda aprobación y publica."""

    CONTENT_PROMPT: ClassVar[str] = (
        "Eres un Growth Hacker experto en comunidades técnicas. "
        "Genera posts auténticos (no spammy). "
        "X: ≤280 chars, URL, 2-3 hashtags. Reddit: título + valor genuino, nunca spam. "
        "Tono developer-to-developer. Incluir URL del deploy. "
        "Output: JSON lista de objetos {platform, content, subreddit, thread_title}."
    )

    def __init__(
        self,
        llm_client: LLMClient,
        x_source: XSource,
        reddit_source: RedditSource,
        checkpoint_manager: CheckpointManager,
    ) -> None:
        self._llm = llm_client
        self._x = x_source
        self._reddit = reddit_source
        self._checkpoints = checkpoint_manager

    async def run(self, mission: Mission) -> Mission:
        """Pipeline principal: generar → draft → checkpoint → publicar."""
        blueprint_raw = read_file(f"missions/{mission.mission_id}/blueprint.yaml")
        blueprint = yaml.safe_load(blueprint_raw)

        deploy_raw = read_file(f"missions/{mission.mission_id}/deploy_result.yaml")
        deploy = yaml.safe_load(deploy_raw)
        deploy_url: str = deploy.get("url", "")

        posts = await self._generate_posts(blueprint, deploy_url)

        draft_path = f"missions/{mission.mission_id}/social_posts.yaml"
        write_file(draft_path, yaml.dump([p.model_dump(mode="json") for p in posts]))
        mission.log.append(LogEntry(
            agent=AgentRole.INFILTRADO,
            event="social_posts_draft_saved",
            artifact=draft_path,
        ))

        await self._checkpoints.trigger(
            mission=mission,
            reason="Aprobar mensajes de marketing antes de publicar en redes sociales.",
            triggered_by="phase_gate",
            blocking_agent=AgentRole.INFILTRADO,
        )
        return mission

    async def publish(self, mission: Mission) -> Mission:
        """Publica posts aprobados. Llamar solo tras resolución del checkpoint."""
        draft_path = f"missions/{mission.mission_id}/social_posts.yaml"
        raw = read_file(draft_path)
        posts = [SocialPost(**p) for p in yaml.safe_load(raw)]

        published = await self._publish_approved_posts(posts, mission)

        write_file(draft_path, yaml.dump([p.model_dump(mode="json") for p in published]))
        mission.log.append(LogEntry(
            agent=AgentRole.INFILTRADO,
            event="social_posts_published",
            artifact=draft_path,
        ))
        return mission

    async def _generate_posts(
        self, blueprint: dict, deploy_url: str
    ) -> list[SocialPost]:
        from core.llm_client import LLMRequest

        user_msg = (
            f"Producto: {blueprint.get('product_name', 'Unknown')}\n"
            f"Problema: {blueprint.get('problem_statement', '')}\n"
            f"URL: {deploy_url}\n"
            "Genera 2 variantes para X y 1 post para Reddit."
        )
        response = await self._llm.complete(LLMRequest(
            role=AgentRole.INFILTRADO,
            system_prompt=self.CONTENT_PROMPT,
            user_message=user_msg,
        ))

        try:
            data = json.loads(response.content)
            return [SocialPost(**item) for item in data]
        except Exception:
            logger.warning("LLM output parse failed; returning empty posts list.")
            return []

    async def _publish_approved_posts(
        self, posts: list[SocialPost], mission: Mission
    ) -> list[SocialPost]:
        results: list[SocialPost] = []
        for post in posts:
            if not post.approved:
                results.append(post)
                continue
            try:
                if post.platform == "x":
                    post = await self._post_to_x(post)
                elif post.platform == "reddit":
                    post = await self._post_to_reddit(post)
            except Exception as exc:
                logger.error("Failed to publish %s post: %s", post.platform, exc)
            results.append(post)
        return results

    async def _post_to_x(self, post: SocialPost) -> SocialPost:
        token = self._x._settings.x_api_key.get_secret_value()
        async with httpx.AsyncClient(base_url="https://api.twitter.com/2") as client:
            resp = await client.post(
                "/tweets",
                json={"text": post.content},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()
        post.published_at = datetime.now(tz=timezone.utc)  # noqa: UP017
        post.post_url = f"https://twitter.com/i/web/status/{data['data']['id']}"
        return post

    async def _post_to_reddit(self, post: SocialPost) -> SocialPost:
        token = await self._reddit._get_token()
        async with httpx.AsyncClient(base_url="https://oauth.reddit.com") as client:
            resp = await client.post(
                "/api/submit",
                data={
                    "kind": "self",
                    "sr": post.subreddit or "SaaS",
                    "title": post.thread_title or post.content[:100],
                    "text": post.content,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()
        post.published_at = datetime.now(tz=timezone.utc)  # noqa: UP017
        post.post_url = (
            data.get("jquery", [[]] * 11)[10][3] if "jquery" in data else None
        )
        return post
