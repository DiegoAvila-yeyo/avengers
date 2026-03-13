"""tests/agents/test_nick_fury.py — Suite de tests para NickFuryOrchestrator.

Cobertura objetivo: ≥ 90% de agents/nick_fury.py
Convenciones: asyncio_mode = "auto" (pyproject.toml), sin BD real.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test-openai-key-for-tests")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-anthropic-key-for-tests")
os.environ.setdefault("REDDIT_CLIENT_ID", "test-reddit-id-abc123")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "test-reddit-secret-abc123")
os.environ.setdefault("X_API_KEY", "test-x-api-key-abc123")
os.environ.setdefault("X_API_SECRET", "test-x-api-secret-abc123")
os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017/avengers_test")

from agents.nick_fury import NickFuryOrchestrator  # noqa: E402
from core.exceptions import (  # noqa: E402
    AgentExecutionError,
    BlueprintNotApprovedError,
    RetryExhaustedError,
)
from core.models import AgentRole, Mission, MissionPhase, MissionStatus  # noqa: E402
from core.state_log import StateLogManager  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_orchestrator() -> tuple[NickFuryOrchestrator, AsyncMock, StateLogManager]:
    repo = AsyncMock()
    repo.save_mission = AsyncMock(return_value="mission-test")
    repo.get_mission = AsyncMock()
    state_log = StateLogManager(repo)
    orch = NickFuryOrchestrator(repo=repo, state_log=state_log)
    return orch, repo, state_log


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_dispatch_success_first_attempt() -> None:
    """dispatch exitoso en primer intento — retry_policy.attempt == 0."""
    orch, repo, _ = _make_orchestrator()
    mission = Mission()
    agent_fn = AsyncMock(return_value=mission)

    result = await orch.dispatch(mission, AgentRole.THOR, agent_fn)

    agent_fn.assert_awaited_once()
    assert result.status == MissionStatus.IN_PROGRESS
    assert result.retry_policy.attempt == 0
    repo.save_mission.assert_awaited()


async def test_dispatch_retries_on_failure() -> None:
    """dispatch con 2 fallos y éxito en 3er intento."""
    orch, repo, _ = _make_orchestrator()
    mission = Mission()

    call_count = 0

    async def flaky_agent(m: Mission) -> Mission:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise AgentExecutionError(AgentRole.THOR, "timeout", call_count - 1)
        return m

    with patch("agents.nick_fury.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await orch.dispatch(mission, AgentRole.THOR, flaky_agent)

    assert call_count == 3
    assert result.status == MissionStatus.IN_PROGRESS
    assert mock_sleep.await_count == 2


async def test_dispatch_exhausted_raises_and_marks_failed() -> None:
    """dispatch agota reintentos → lanza RetryExhaustedError, status=FAILED."""
    orch, repo, _ = _make_orchestrator()
    mission = Mission()

    async def always_fail(m: Mission) -> Mission:
        raise AgentExecutionError(AgentRole.THOR, "crash", 0)

    with patch("agents.nick_fury.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RetryExhaustedError) as exc_info:
            await orch.dispatch(mission, AgentRole.THOR, always_fail)

    assert exc_info.value.agent == AgentRole.THOR
    assert mission.status == MissionStatus.FAILED
    repo.save_mission.assert_awaited()


async def test_advance_phase_blocks_without_approved_blueprint() -> None:
    """advance_phase de 2→3 sin blueprint aprobado → BlueprintNotApprovedError."""
    orch, _, _ = _make_orchestrator()
    mission = Mission(current_phase=MissionPhase.CAPTAIN_AMERICA)
    mission.blueprint_ref = None
    mission.approved_by_human = False

    with pytest.raises(BlueprintNotApprovedError):
        await orch.advance_phase(mission)


async def test_every_state_change_persists() -> None:
    """Cada cambio de estado llama repo.save_mission (mock verify)."""
    orch, repo, _ = _make_orchestrator()
    mission = Mission()

    await orch.mark_awaiting_human(mission, "needs review")

    repo.save_mission.assert_awaited()
    assert mission.status == MissionStatus.AWAITING_HUMAN


async def test_resume_from_checkpoint() -> None:
    """resume_from_checkpoint recupera misión desde repo."""
    orch, repo, _ = _make_orchestrator()
    stored = Mission(status=MissionStatus.REVIEW)
    stored.log.append(MagicMock())
    repo.get_mission.return_value = stored

    result = await orch.resume_from_checkpoint(stored.mission_id)

    repo.get_mission.assert_awaited_once_with(stored.mission_id)
    assert result.status == MissionStatus.REVIEW


async def test_exponential_backoff_delays() -> None:
    """backoff delay es exponencial (2s, 4s) — mockear asyncio.sleep."""
    orch, _, _ = _make_orchestrator()
    mission = Mission()
    call_count = 0

    async def fail_twice(m: Mission) -> Mission:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise AgentExecutionError(AgentRole.THOR, "err", call_count - 1)
        return m

    delays: list[float] = []

    async def capture_sleep(seconds: float) -> None:
        delays.append(seconds)

    with patch("agents.nick_fury.asyncio.sleep", side_effect=capture_sleep):
        await orch.dispatch(mission, AgentRole.THOR, fail_twice)

    assert delays[0] == 2.0  # base_delay * 2^0
    assert delays[1] == 4.0  # base_delay * 2^1
