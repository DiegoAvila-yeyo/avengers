"""tests/agents/test_api_fabricator.py — Suite de tests para ApiFabricatorAgent.

Cobertura: generación desde URL, split de conectores largos, URL inaccesible,
ROOT JAIL, imports desconocidos, archivo sin métodos async.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test-openai-key-for-tests")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-anthropic-key-for-tests")
os.environ.setdefault("REDDIT_CLIENT_ID", "test-reddit-id-abc123")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "test-reddit-secret-abc123")
os.environ.setdefault("X_API_KEY", "test-x-api-key-abc123")
os.environ.setdefault("X_API_SECRET", "test-x-api-secret-abc123")
os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017/avengers_test")

from agents.api_fabricator import ApiFabricatorAgent  # noqa: E402
from core.exceptions import AgentExecutionError  # noqa: E402
from core.models import Mission, MissionStatus  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ── Helpers ───────────────────────────────────────────────────────────────────

_SIMPLE_CONNECTOR = textwrap.dedent("""\
    import httpx

    class StripeConnector:
        def __init__(self, api_key: str) -> None:
            self._api_key = api_key

        async def list_charges(self) -> dict:
            async with httpx.AsyncClient() as client:
                r = await client.get("https://api.stripe.com/v1/charges",
                                     headers={"Authorization": f"Bearer {self._api_key}"})
                r.raise_for_status()
                return r.json()
""")

_LONG_CONNECTOR = ("async def stub() -> None: ...\n") * 260  # >250 lines


def _make_mission() -> Mission:
    return Mission(
        mission_id="m-fab-test",
        status=MissionStatus.IN_PROGRESS,
        output_dir="output/",
    )


def _make_agent(llm_response: str = _SIMPLE_CONNECTOR) -> ApiFabricatorAgent:
    llm = MagicMock()
    llm_resp = MagicMock()
    llm_resp.content = llm_response
    llm.complete = AsyncMock(return_value=llm_resp)
    return ApiFabricatorAgent(llm_client=llm, project_root=PROJECT_ROOT)


# ── Test 1: generate_connector desde URL ─────────────────────────────────────

async def test_generate_connector_from_url(tmp_path: Path) -> None:
    agent = _make_agent()
    mission = _make_mission()

    with (
        patch("agents.api_fabricator.httpx.AsyncClient") as mock_client,
        patch("agents.api_fabricator.write_file") as mock_write,
        patch("agents.api_fabricator.resolve_safe_path",
              return_value=tmp_path / "stripe_connector.py"),
    ):
        response_mock = MagicMock()
        response_mock.text = "openapi: 3.0.0"
        response_mock.raise_for_status = MagicMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            get=AsyncMock(return_value=response_mock)
        ))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await agent.generate_connector(
            "stripe", "https://stripe.com/openapi.json", mission
        )

    mock_write.assert_called_once()
    assert "connector_generated" in [e.event for e in mission.log]
    assert isinstance(result, Path)


# ── Test 2: conector >250L → LLM solicitado a dividir ────────────────────────

async def test_oversized_connector_triggers_split_request(tmp_path: Path) -> None:
    llm = MagicMock()
    short_code = _SIMPLE_CONNECTOR
    long_code = _LONG_CONNECTOR

    call_count = 0

    async def _complete(req: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.content = long_code if call_count == 1 else short_code
        return resp

    llm.complete = _complete
    agent = ApiFabricatorAgent(llm_client=llm, project_root=PROJECT_ROOT)
    mission = _make_mission()

    with (
        patch("agents.api_fabricator.write_file"),
        patch("agents.api_fabricator.resolve_safe_path", return_value=tmp_path / "x.py"),
    ):
        await agent.generate_connector("big_api", "raw docs", mission)

    assert call_count == 2  # 1 initial + 1 split request


# ── Test 3: URL inaccesible → AgentExecutionError ────────────────────────────

async def test_inaccessible_url_raises_agent_execution_error() -> None:
    import httpx as _httpx

    agent = _make_agent()
    mission = _make_mission()

    with patch("agents.api_fabricator.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            side_effect=_httpx.ConnectError("connection refused")
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(AgentExecutionError, match="URL inaccesible"):
            await agent.generate_connector("broken_api", "https://unreachable.example.com", mission)


# ── Test 4: conector escrito SOLO en tools/connectors/ (ROOT JAIL) ────────────

async def test_connector_written_inside_root_jail() -> None:
    agent = _make_agent()
    mission = _make_mission()
    written_paths: list[str] = []

    def _capture_write(path: str, content: str) -> Path:
        written_paths.append(str(path))
        return PROJECT_ROOT / path

    with (
        patch("agents.api_fabricator.write_file", side_effect=_capture_write),
        patch("agents.api_fabricator.resolve_safe_path", side_effect=lambda p: PROJECT_ROOT / p),
    ):
        await agent.generate_connector("payments", "raw docs", mission)

    assert all("tools/connectors" in p for p in written_paths)


# ── Test 5: validate_connector rechaza imports desconocidos ──────────────────

async def test_validate_rejects_unknown_imports(tmp_path: Path) -> None:
    connector = tmp_path / "bad_connector.py"
    connector.write_text("import requests\n\nasync def fetch() -> None: ...\n")
    agent = _make_agent()

    with (
        patch("agents.api_fabricator.resolve_safe_path", return_value=connector),
        pytest.raises(AgentExecutionError, match="Import desconocido"),
    ):
        await agent.validate_connector("tools/connectors/bad_connector.py")


# ── Test 6: validate_connector rechaza archivo sin métodos async ──────────────

async def test_validate_rejects_no_async_methods(tmp_path: Path) -> None:
    connector = tmp_path / "sync_connector.py"
    connector.write_text("import httpx\n\ndef fetch() -> None: ...\n")
    agent = _make_agent()

    with (
        patch("agents.api_fabricator.resolve_safe_path", return_value=connector),
        pytest.raises(AgentExecutionError, match="no tiene métodos async"),
    ):
        await agent.validate_connector("tools/connectors/sync_connector.py")
