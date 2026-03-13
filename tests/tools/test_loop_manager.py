"""tests/tools/test_loop_manager.py — Tests para LoopManager (Prompt #24)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import AgentRole, Mission, MissionStatus
from tools.feedback_collector import FeedbackSummary
from tools.loop_manager import LoopManager, MissionSummary


def _make_feedback(
    positive_ratio: float = 0.6,
    coverage_pct: float | None = None,
    pain_points: list[str] | None = None,
) -> FeedbackSummary:
    return FeedbackSummary(
        mission_id="m-test",
        total_items=10,
        positive_ratio=positive_ratio,
        feature_requests=["dark mode"],
        pain_points=pain_points or ["slow load"],
        suggested_keyword="performance",
        generated_at=datetime.now(tz=timezone.utc),  # noqa: UP017
    )


def _make_summary(
    coverage_pct: float = 85.0,
    total_tokens_used: int = 5000,
) -> MissionSummary:
    return MissionSummary(
        mission_id="m-test",
        product_name="test-product",
        status=MissionStatus.DONE,
        total_tokens_used=total_tokens_used,
        total_duration_seconds=120.0,
        artifacts_created=3,
        tests_passing=5,
        coverage_pct=coverage_pct,
        deploy_url=None,
        feedback_summary_ref=None,
        closed_at=datetime.now(tz=timezone.utc),  # noqa: UP017
    )


def _make_loop_manager() -> tuple[LoopManager, MagicMock, MagicMock, MagicMock]:
    orchestrator = MagicMock()
    checkpoint_manager = MagicMock()
    repo = MagicMock()
    manager = LoopManager(
        orchestrator=orchestrator,
        checkpoint_manager=checkpoint_manager,
        repo=repo,
    )
    return manager, orchestrator, checkpoint_manager, repo


@pytest.mark.asyncio
async def test_close_mission_sets_done_and_saves_summary() -> None:
    """close_mission() cambia status a DONE y guarda mission_summary.yaml."""
    manager, _, _, repo = _make_loop_manager()
    repo.update_status = AsyncMock(return_value=True)

    mission = Mission(mission_id="m-001")

    with (
        patch("tools.loop_manager.read_file", side_effect=FileNotFoundError),
        patch("tools.loop_manager.write_file") as mock_write,
        patch("tools.loop_manager.resolve_safe_path") as mock_rsp,
    ):
        mock_rsp.return_value = MagicMock(exists=MagicMock(return_value=False))
        summary = await manager.close_mission(mission)

    assert mission.status == MissionStatus.DONE
    assert summary.mission_id == "m-001"
    assert summary.status == MissionStatus.DONE
    repo.update_status.assert_awaited_once_with("m-001", MissionStatus.DONE)
    written_paths = [call.args[0] for call in mock_write.call_args_list]
    assert any("mission_summary.yaml" in p for p in written_paths)


@pytest.mark.asyncio
async def test_close_mission_cleans_cache_not_blueprints() -> None:
    """close_mission() limpia scrape_cache pero NO toca blueprints ni outputs."""
    manager, _, _, repo = _make_loop_manager()
    repo.update_status = AsyncMock(return_value=True)

    mission = Mission(mission_id="m-cache")

    mock_cache_path = MagicMock()
    mock_cache_path.exists.return_value = True

    with (
        patch("tools.loop_manager.read_file", side_effect=FileNotFoundError),
        patch("tools.loop_manager.write_file"),
        patch("tools.loop_manager.resolve_safe_path", return_value=mock_cache_path),
        patch("tools.loop_manager.shutil.rmtree") as mock_rmtree,
    ):
        await manager.close_mission(mission)

    mock_rmtree.assert_called_once_with(mock_cache_path)


def test_evaluate_returns_false_on_low_traction() -> None:
    """evaluate_next_cycle() retorna False si positive_ratio < 0.4."""
    manager, _, _, _ = _make_loop_manager()
    feedback = _make_feedback(positive_ratio=0.2)
    summary = _make_summary(coverage_pct=85.0, total_tokens_used=5000)

    assert manager.evaluate_next_cycle(summary, feedback) is False


@pytest.mark.asyncio
async def test_launch_triggers_checkpoint_first() -> None:
    """launch_next_cycle() dispara el checkpoint antes de crear la nueva misión."""
    manager, orchestrator, checkpoint_manager, repo = _make_loop_manager()

    call_order: list[str] = []

    async def mock_trigger(**kwargs: object) -> MagicMock:
        call_order.append("checkpoint")
        return MagicMock()

    async def mock_create_mission(**kwargs: object) -> Mission:
        call_order.append("create_mission")
        return Mission(mission_id="m-new")

    checkpoint_manager.trigger = mock_trigger
    orchestrator.create_mission = mock_create_mission
    repo.append_log = AsyncMock(return_value=True)

    feedback = _make_feedback(positive_ratio=0.8)
    summary = _make_summary(coverage_pct=85.0)

    await manager.launch_next_cycle(summary, feedback)

    assert call_order[0] == "checkpoint", "El checkpoint debe ser la primera instrucción"
    assert call_order[1] == "create_mission"


@pytest.mark.asyncio
async def test_launch_injects_feedback_keyword() -> None:
    """launch_next_cycle() inyecta el keyword de feedback en el StateLog."""
    manager, orchestrator, checkpoint_manager, repo = _make_loop_manager()
    checkpoint_manager.trigger = AsyncMock(return_value=MagicMock())
    new_mission = Mission(mission_id="m-new")
    orchestrator.create_mission = AsyncMock(return_value=new_mission)
    repo.append_log = AsyncMock(return_value=True)

    feedback = _make_feedback(positive_ratio=0.8, pain_points=["issue A", "issue B"])
    summary = _make_summary(coverage_pct=85.0)

    result = await manager.launch_next_cycle(summary, feedback)

    keyword_entries = [e for e in result.log if e.event == "loop_feedback_keyword"]
    assert len(keyword_entries) == 1
    assert keyword_entries[0].artifact == "performance"
    assert keyword_entries[0].agent == AgentRole.NICK_FURY.value


@pytest.mark.asyncio
async def test_factory_report_aggregates_completed_missions() -> None:
    """generate_factory_report() lee misiones DONE y FAILED y escribe el doc."""
    manager, _, _, repo = _make_loop_manager()

    now = datetime.now(tz=timezone.utc)  # noqa: UP017
    m1 = Mission(mission_id="m-001", status=MissionStatus.DONE)
    m1.updated_at = now
    m2 = Mission(mission_id="m-002", status=MissionStatus.FAILED)

    repo.list_by_status = AsyncMock(side_effect=lambda s: [m1] if s == MissionStatus.DONE else [m2])

    with patch("tools.loop_manager.write_file") as mock_write:
        report = await manager.generate_factory_report()

    assert "Misiones completadas: 1" in report
    assert "Misiones fallidas: 1" in report
    written_paths = [call.args[0] for call in mock_write.call_args_list]
    assert "docs/factory_report.md" in written_paths
