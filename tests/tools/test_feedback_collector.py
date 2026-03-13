"""tests/tools/test_feedback_collector.py — Tests para FeedbackCollector y FeedbackAnalyzer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.feedback_analyzer import FeedbackAnalyzer
from tools.feedback_collector import FeedbackCollector, FeedbackItem, FeedbackSummary


def _make_social_post(platform: str, post_url: str) -> MagicMock:
    post = MagicMock()
    post.platform = platform
    post.post_url = post_url
    return post


def _make_x_source() -> MagicMock:
    x = MagicMock()
    x._settings.x_api_key.get_secret_value.return_value = "fake-token"
    return x


def _make_reddit_source(token: str = "reddit-token") -> MagicMock:
    reddit = MagicMock()
    reddit._get_token = AsyncMock(return_value=token)
    return reddit


def _make_feedback_items(n: int = 5, base_engagement: int = 10) -> list[FeedbackItem]:
    now = datetime.now(tz=timezone.utc)  # noqa: UP017
    return [
        FeedbackItem(
            source="x", post_url="https://x.com/status/123",
            content=f"Comment {i}", author=f"user{i}",
            engagement=base_engagement + i, collected_at=now,
        )
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_collect_calls_all_sources() -> None:
    """collect() invoca _collect_x_replies y _collect_reddit_comments para los posts."""
    x_source = _make_x_source()
    reddit_source = _make_reddit_source()
    collector = FeedbackCollector(x_source=x_source, reddit_source=reddit_source)

    x_post = _make_social_post("x", "https://twitter.com/i/web/status/111")
    reddit_post = _make_social_post("reddit", "https://reddit.com/r/SaaS/comments/abc/post")

    with (
        patch.object(
            collector, "_collect_x_replies", new_callable=AsyncMock, return_value=[]
        ) as mock_x,
        patch.object(
            collector, "_collect_reddit_comments", new_callable=AsyncMock, return_value=[]
        ) as mock_r,
    ):
        await collector.collect([x_post, reddit_post])

    mock_x.assert_awaited_once_with(x_post)
    mock_r.assert_awaited_once_with(reddit_post)


@pytest.mark.asyncio
async def test_analyze_uses_top_30_signals() -> None:
    """analyze() pasa solo los top 30 comentarios por engagement al LLM (JIT)."""
    items = _make_feedback_items(n=40, base_engagement=0)
    llm_client = MagicMock()
    summary_data = {
        "positive_ratio": 0.7,
        "feature_requests": ["dark mode"],
        "pain_points": ["slow load"],
        "suggested_keyword": "performance",
    }
    llm_client.complete = AsyncMock(return_value=MagicMock(content=json.dumps(summary_data)))

    analyzer = FeedbackAnalyzer(llm_client=llm_client)

    with patch("tools.feedback_analyzer.write_file"):
        await analyzer.analyze(items, mission_id="m-test")

    called_msg = json.loads(llm_client.complete.call_args[0][0].user_message)
    assert len(called_msg) == 30


def test_to_pain_signals_creates_signals() -> None:
    """to_pain_signals() crea un PainSignal por cada feature_request y pain_point."""
    import asyncio
    x_source = _make_x_source()
    reddit_source = _make_reddit_source()
    collector = FeedbackCollector(x_source=x_source, reddit_source=reddit_source)

    summary = FeedbackSummary(
        mission_id="m-001",
        total_items=10,
        positive_ratio=0.6,
        feature_requests=["dark mode", "export CSV"],
        pain_points=["slow API"],
        suggested_keyword="performance",
        generated_at=datetime.now(tz=timezone.utc),  # noqa: UP017
    )

    signals = asyncio.get_event_loop().run_until_complete(collector.to_pain_signals(summary))
    assert len(signals) == 3
    assert all(s.source == "feedback_loop" for s in signals)
    contents = [s.content for s in signals]
    assert "dark mode" in contents
    assert "export CSV" in contents
    assert "slow API" in contents


@pytest.mark.asyncio
async def test_summary_saved_to_correct_path() -> None:
    """analyze() guarda feedback_summary.yaml en missions/{id}/."""
    items = _make_feedback_items(n=5)
    llm_client = MagicMock()
    summary_data = {
        "positive_ratio": 0.8,
        "feature_requests": [],
        "pain_points": [],
        "suggested_keyword": "automation",
    }
    llm_client.complete = AsyncMock(return_value=MagicMock(content=json.dumps(summary_data)))

    analyzer = FeedbackAnalyzer(llm_client=llm_client)

    with patch("tools.feedback_analyzer.write_file") as mock_write:
        await analyzer.analyze(items, mission_id="m-042")

    mock_write.assert_called_once()
    path_arg = mock_write.call_args[0][0]
    assert path_arg == "missions/m-042/feedback_summary.yaml"


@pytest.mark.asyncio
async def test_collect_handles_empty_responses() -> None:
    """collect() retorna lista vacía cuando posts no tienen post_url o fuentes vacías."""
    x_source = _make_x_source()
    reddit_source = _make_reddit_source()
    collector = FeedbackCollector(x_source=x_source, reddit_source=reddit_source)

    post_no_url = _make_social_post("x", None)
    post_no_url.post_url = None

    result = await collector.collect([post_no_url])
    assert result == []
