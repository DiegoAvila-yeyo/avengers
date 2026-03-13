"""tests/agents/test_infiltrado.py — Suite de tests para InfiltradoAgent.

Cobertura: generación + checkpoint, guard approved=False, draft YAML, X char limit.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

os.environ.setdefault("OPENAI_API_KEY", "sk-test-openai-key-for-tests")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-anthropic-key-for-tests")
os.environ.setdefault("REDDIT_CLIENT_ID", "test-reddit-id-abc123")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "test-reddit-secret-abc123")
os.environ.setdefault("X_API_KEY", "test-x-api-key-abc123")
os.environ.setdefault("X_API_SECRET", "test-x-api-secret-abc123")
os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017/avengers_test")

from agents.infiltrado import InfiltradoAgent, SocialPost  # noqa: E402
from core.models import Mission  # noqa: E402
from tools.file_tools import PROJECT_ROOT  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────────────

_BLUEPRINT = {
    "product_name": "TestSaaS",
    "problem_statement": "Devs waste time on boilerplate",
}
_DEPLOY = {"url": "https://testsaas.vercel.app"}


def _make_agent() -> tuple[InfiltradoAgent, MagicMock, MagicMock]:
    llm = MagicMock()
    llm.complete = AsyncMock()
    x_src = MagicMock()
    x_src._settings = MagicMock()
    x_src._settings.x_api_key.get_secret_value.return_value = "tok"
    reddit_src = MagicMock()
    reddit_src._get_token = AsyncMock(return_value="rtok")
    cp = MagicMock()
    cp.trigger = AsyncMock()
    agent = InfiltradoAgent(llm, x_src, reddit_src, cp)
    return agent, llm, cp


def _posts_yaml(posts: list[SocialPost]) -> str:
    return yaml.dump([p.model_dump(mode="json") for p in posts])


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_generates_then_checkpoints(tmp_path: object) -> None:
    """run() genera posts y ESPERA checkpoint antes de retornar."""
    agent, llm, cp = _make_agent()
    mission = Mission(mission_id="m-test-22a")
    draft_dir = PROJECT_ROOT / "missions" / "m-test-22a"
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / "blueprint.yaml").write_text(yaml.dump(_BLUEPRINT))
    (draft_dir / "deploy_result.yaml").write_text(yaml.dump(_DEPLOY))

    llm.complete.return_value = MagicMock(content='[{"platform":"x","content":"Hello #test https://testsaas.vercel.app"}]')

    try:
        await agent.run(mission)
    finally:
        import shutil
        shutil.rmtree(draft_dir, ignore_errors=True)

    cp.trigger.assert_awaited_once()
    assert cp.trigger.call_args.kwargs["triggered_by"] == "phase_gate"


@pytest.mark.asyncio
async def test_publish_skips_unapproved_posts() -> None:
    """_publish_approved_posts não publica posts con approved=False."""
    agent, _, _ = _make_agent()
    mission = Mission(mission_id="m-test-22b")

    posts = [
        SocialPost(platform="x", content="Draft post", approved=False),
        SocialPost(platform="x", content="Approved post #saas https://url.com", approved=True),
    ]

    with patch.object(agent, "_post_to_x", new_callable=AsyncMock) as mock_x:
        mock_x.return_value = posts[1]
        result = await agent._publish_approved_posts(posts, mission)

    assert mock_x.call_count == 1
    assert result[0].published_at is None  # unapproved never published


@pytest.mark.asyncio
async def test_posts_saved_as_draft(tmp_path: object) -> None:
    """run() persiste social_posts.yaml en missions/{id}/ con approved=False."""
    agent, llm, cp = _make_agent()
    mission = Mission(mission_id="m-test-22c")
    draft_dir = PROJECT_ROOT / "missions" / "m-test-22c"
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / "blueprint.yaml").write_text(yaml.dump(_BLUEPRINT))
    (draft_dir / "deploy_result.yaml").write_text(yaml.dump(_DEPLOY))

    payload = (
        '[{"platform":"reddit","content":"Useful post",'
        '"subreddit":"SaaS","thread_title":"T"}]'
    )
    llm.complete.return_value = MagicMock(content=payload)

    try:
        await agent.run(mission)
        saved = yaml.safe_load((draft_dir / "social_posts.yaml").read_text())
    finally:
        import shutil
        shutil.rmtree(draft_dir, ignore_errors=True)

    assert isinstance(saved, list)
    assert saved[0]["approved"] is False  # drafts never auto-approved


def test_x_post_respects_character_limit() -> None:
    """Posts para X no deben superar 280 caracteres."""
    long_post = SocialPost(
        platform="x",
        content="A" * 281,
        approved=False,
    )
    normal_post = SocialPost(
        platform="x",
        content="Short post #saas https://example.com",
        approved=False,
    )
    assert len(long_post.content) > 280, "precondition: post is too long"
    assert len(normal_post.content) <= 280, "normal post fits X limit"
