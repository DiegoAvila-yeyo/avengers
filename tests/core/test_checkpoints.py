"""tests/core/test_checkpoints.py — Suite de tests para CheckpointManager.

Cobertura: trigger, resolve (resume/abort/retry_override), get_pending.
Sin BD real — todo mockeado con AsyncMock.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock

os.environ.setdefault("OPENAI_API_KEY", "sk-test-openai-key-for-tests")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-anthropic-key-for-tests")
os.environ.setdefault("REDDIT_CLIENT_ID", "test-reddit-id-abc123")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "test-reddit-secret-abc123")
os.environ.setdefault("X_API_KEY", "test-x-api-key-abc123")
os.environ.setdefault("X_API_SECRET", "test-x-api-secret-abc123")
os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017/avengers_test")

from core.checkpoints import (  # noqa: E402
    CheckpointManager,
    CheckpointRecord,
)
from core.models import AgentRole, Mission, MissionStatus  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_manager() -> tuple[CheckpointManager, AsyncMock, AsyncMock, AsyncMock]:
    """Crea CheckpointManager con repo, col y notifier mockeados."""
    repo = AsyncMock()
    repo.save_mission = AsyncMock()

    col = AsyncMock()
    col.insert_one = AsyncMock()
    col.update_one = AsyncMock()

    notifier = AsyncMock()
    notifier.notify = AsyncMock()

    manager = CheckpointManager(repo=repo, notifier=notifier, checkpoint_col=col)
    return manager, repo, col, notifier


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_trigger_creates_record_and_sets_awaiting() -> None:
    """trigger → crea CheckpointRecord y pone mission.status = AWAITING_HUMAN."""
    manager, repo, col, _ = _make_manager()
    mission = Mission()

    record = await manager.trigger(
        mission=mission,
        reason="agotados los reintentos",
        triggered_by="retry_exhausted",
        blocking_agent=AgentRole.THOR,
        retry_attempts=3,
    )

    assert isinstance(record, CheckpointRecord)
    assert record.mission_id == mission.mission_id
    assert record.blocking_agent == AgentRole.THOR
    assert record.retry_attempts == 3
    assert mission.status == MissionStatus.AWAITING_HUMAN
    col.insert_one.assert_awaited_once()
    repo.save_mission.assert_awaited_once_with(mission)


async def test_trigger_calls_notifier() -> None:
    """trigger → llama notifier.notify() con el CheckpointRecord correcto."""
    manager, _, _, notifier = _make_manager()
    mission = Mission()

    record = await manager.trigger(
        mission=mission,
        reason="revisión manual",
        triggered_by="phase_gate",
        blocking_agent=AgentRole.CAPTAIN_AMERICA,
    )

    notifier.notify.assert_awaited_once_with(record)


async def test_trigger_persists_even_if_notifier_fails() -> None:
    """trigger con notifier fallido → CheckpointRecord YA persistido en DB."""
    manager, repo, col, notifier = _make_manager()
    notifier.notify.side_effect = RuntimeError("Slack no disponible")
    mission = Mission()

    record = await manager.trigger(
        mission=mission,
        reason="fallo de notificación",
        triggered_by="manual",
        blocking_agent=AgentRole.IRON_CODER,
    )

    # La persistencia ocurrió ANTES de la notificación fallida
    assert isinstance(record, CheckpointRecord)
    col.insert_one.assert_awaited_once()
    repo.save_mission.assert_awaited_once_with(mission)
    assert mission.status == MissionStatus.AWAITING_HUMAN


async def test_resolve_resume_sets_in_progress() -> None:
    """resolve 'resume' → mission.status = IN_PROGRESS."""
    manager, repo, col, _ = _make_manager()
    mission = Mission(status=MissionStatus.AWAITING_HUMAN)

    result = await manager.resolve(
        checkpoint_id="cp-001",
        resolution="resume",
        mission=mission,
    )

    assert result.status == MissionStatus.IN_PROGRESS
    repo.save_mission.assert_awaited_once_with(mission)
    col.update_one.assert_awaited_once()


async def test_resolve_abort_sets_aborted() -> None:
    """resolve 'abort' → mission.status = ABORTED."""
    manager, repo, _, _ = _make_manager()
    mission = Mission(status=MissionStatus.AWAITING_HUMAN)

    result = await manager.resolve(
        checkpoint_id="cp-002",
        resolution="abort",
        mission=mission,
    )

    assert result.status == MissionStatus.ABORTED
    repo.save_mission.assert_awaited_once_with(mission)


async def test_resolve_retry_override_resets_policy() -> None:
    """resolve 'retry_override' → retry_policy reseteada y status = IN_PROGRESS."""
    manager, repo, _, _ = _make_manager()
    mission = Mission(status=MissionStatus.AWAITING_HUMAN)
    # Simula política agotada
    mission.retry_policy.attempt = 3

    result = await manager.resolve(
        checkpoint_id="cp-003",
        resolution="retry_override",
        mission=mission,
    )

    assert result.status == MissionStatus.IN_PROGRESS
    assert result.retry_policy.attempt == 0  # política reseteada
    repo.save_mission.assert_awaited_once_with(mission)
