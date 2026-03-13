"""tests/agents/test_thor.py — Suite de tests para ThorAgent.

Cobertura: generación de brief.yaml, ordenamiento por engagement, reintentos JSON.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
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

from agents.thor import ThorAgent  # noqa: E402
from core.brief_schema import BriefV1  # noqa: E402
from core.exceptions import AgentExecutionError  # noqa: E402
from core.models import Mission  # noqa: E402
from tools.sources import PainSignal  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_signal(engagement: int, source: str = "reddit") -> PainSignal:
    return PainSignal(
        source=source,
        content="test signal content",
        url="https://example.com",
        engagement=engagement,
        author="testuser",
        collected_at=datetime.now(tz=timezone.utc),
        keywords=["test"],
    )


def _valid_llm_response() -> str:
    return json.dumps({
        "pain_points": ["pain1", "pain2"],
        "opportunities": ["opp1"],
        "recommended_niche": "SaaS automation",
        "keywords_expanded": ["saas", "automation"],
    })


def _mock_llm(content: str) -> AsyncMock:
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=MagicMock(content=content))
    return llm


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_run_generates_yaml_at_correct_path(tmp_path: Path) -> None:
    """run() escribe brief.yaml en missions/{id}/brief.yaml (ROOT JAIL)."""
    source = AsyncMock()
    source.search = AsyncMock(return_value=[_make_signal(100)])

    agent = ThorAgent(sources=[source], llm=_mock_llm(_valid_llm_response()))
    mission = Mission()

    with patch("tools.file_tools.PROJECT_ROOT", tmp_path):
        result = await agent.run(mission)

    expected = tmp_path / f"missions/{mission.mission_id}/brief.yaml"
    assert expected.exists(), f"brief.yaml no encontrado en {expected}"

    brief_data = yaml.safe_load(expected.read_text())
    assert brief_data["mission_id"] == mission.mission_id
    assert brief_data["pain_points"] == ["pain1", "pain2"]
    assert result.brief_ref == f"missions/{mission.mission_id}/brief.yaml"


async def test_signals_sorted_by_engagement_descending() -> None:
    """_collect_signals() ordena señales por engagement descendente antes de ir al LLM."""
    source = AsyncMock()
    source.search = AsyncMock(return_value=[
        _make_signal(10),
        _make_signal(500),
        _make_signal(50),
        _make_signal(250),
    ])

    agent = ThorAgent(sources=[source], llm=AsyncMock())
    signals = await agent._collect_signals(["test"])

    engagements = [s.engagement for s in signals]
    assert engagements == sorted(engagements, reverse=True), (
        f"Señales no ordenadas: {engagements}"
    )


async def test_retry_on_invalid_json_succeeds_on_second_attempt() -> None:
    """_extract_brief() reintenta si el LLM devuelve JSON inválido la primera vez."""
    call_count = 0

    async def mock_complete(request: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        content = "NOT VALID JSON <<<" if call_count == 1 else _valid_llm_response()
        return MagicMock(content=content)

    llm = AsyncMock()
    llm.complete = mock_complete

    agent = ThorAgent(sources=[], llm=llm)
    brief = await agent._extract_brief([_make_signal(100)], "mission-retry-test")

    assert call_count == 2, f"Se esperaban 2 llamadas al LLM, se hicieron {call_count}"
    assert isinstance(brief, BriefV1)
    assert brief.mission_id == "mission-retry-test"
    assert brief.recommended_niche == "SaaS automation"


async def test_retry_exhausted_raises_agent_execution_error() -> None:
    """_extract_brief() lanza AgentExecutionError si el JSON sigue inválido tras reintentos."""
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=MagicMock(content="INVALID JSON ALWAYS"))

    agent = ThorAgent(sources=[], llm=llm)

    with pytest.raises(AgentExecutionError) as exc_info:
        await agent._extract_brief([_make_signal(100)], "mission-fail-test")

    assert exc_info.value.agent.value == "thor"
    assert llm.complete.await_count == 3  # 1 intento + 2 reintentos
