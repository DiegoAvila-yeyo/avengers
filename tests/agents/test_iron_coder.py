"""tests/agents/test_iron_coder.py — Suite de tests para IronCoderAgent.

Cobertura: generación módulo a módulo, delegación AMD-04 al API-Fabricator,
propagación de errores, ROOT JAIL, actualización del MAP.yaml.
"""

from __future__ import annotations

import os
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

from agents.iron_coder import IronCoderAgent  # noqa: E402
from core.exceptions import AgentExecutionError, RootJailViolationError  # noqa: E402
from core.models import AgentRole, Mission  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _blueprint_dict(mission_id: str = "m-test", with_unknown_api: bool = False) -> dict:
    endpoints = [
        {
            "method": "GET",
            "path": "/items",
            "description": "List items",
            "response_schema": {"items": "list"},
            "known_api": True,
        }
    ]
    if with_unknown_api:
        endpoints.append(
            {
                "method": "POST",
                "path": "/ext/push",
                "description": "Push to external",
                "response_schema": {"ok": "bool"},
                "known_api": False,
            }
        )
    return {
        "blueprint_id": f"bp-{mission_id}",
        "mission_id": mission_id,
        "product_name": "TestProduct",
        "problem_statement": "Test",
        "target_audience": "Devs",
        "tech_stack": ["Python", "FastAPI"],
        "modules": [
            {
                "module_name": "items_module",
                "responsibility": "Handles items",
                "estimated_lines": 100,
                "external_apis": [],
            }
        ],
        "data_models": [{"name": "Item", "fields": {"id": "str"}}],
        "api_endpoints": endpoints,
        "acceptance_criteria": [{"id": "AC-001", "description": "Items work", "automated": True}],
    }


def _map_dict(mission_id: str = "m-test") -> dict:
    return {
        "mission_id": mission_id,
        "blueprint_id": f"bp-{mission_id}",
        "files": [
            {
                "path": f"output/{mission_id}/items_module.py",
                "created_by": "iron_coder",
                "module": "items_module",
                "responsibility": "Handles items",
                "status": "pending",
            }
        ],
    }


def _mission(mission_id: str = "m-test") -> Mission:
    m = Mission(mission_id=mission_id)
    m.blueprint_ref = f"missions/{mission_id}/blueprint.yaml"
    m.output_dir = "output/"
    return m


def _mock_llm(content: str = "# generated code\n") -> AsyncMock:
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=MagicMock(content=content))
    return llm


def _make_agent(llm: AsyncMock, fabricator: AsyncMock | None = None) -> IronCoderAgent:
    fab = fabricator or AsyncMock()
    return IronCoderAgent(llm_client=llm, api_fabricator=fab, project_root=PROJECT_ROOT)


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_generates_all_modules(tmp_path: Path) -> None:
    """run() itera sobre todos los módulos del Blueprint y crea cada archivo."""
    mission_id = "m-gen"
    mission = _mission(mission_id)
    bp_yaml = yaml.dump(_blueprint_dict(mission_id))
    map_yaml = yaml.dump(_map_dict(mission_id))

    with (
        patch("agents.iron_coder.read_file", side_effect=[bp_yaml]),
        patch("agents.iron_coder.write_file") as mock_write,
        patch("tools.map_tools.read_file", return_value=map_yaml),
        patch("tools.map_tools.write_file"),
    ):
        agent = _make_agent(_mock_llm("# module code\n"))
        result = await agent.run(mission)

    mock_write.assert_called_once()
    written_path = mock_write.call_args[0][0]
    assert "items_module.py" in written_path
    assert any(e.event == "module_created" for e in result.log)


@pytest.mark.asyncio
async def test_unknown_api_triggers_fabricator_invocation() -> None:
    """Módulo con external_apis → _invoke_api_fabricator llamado."""
    mission_id = "m-fab"
    mission = _mission(mission_id)
    bp = _blueprint_dict(mission_id)
    bp["modules"][0]["external_apis"] = ["stripe"]
    bp_yaml = yaml.dump(bp)
    map_yaml = yaml.dump(_map_dict(mission_id))

    fabricator = AsyncMock()
    fabricator.generate_connector = AsyncMock(
        return_value=Path("tools/connectors/stripe_connector.py")
    )

    with (
        patch("agents.iron_coder.read_file", return_value=bp_yaml),
        patch("agents.iron_coder.write_file"),
        patch("tools.map_tools.read_file", return_value=map_yaml),
        patch("tools.map_tools.write_file"),
    ):
        agent = _make_agent(_mock_llm(), fabricator)
        result = await agent.run(mission)

    fabricator.generate_connector.assert_called_once_with("stripe")
    assert any(e.event == "api_fabricator_invoked" for e in result.log)


@pytest.mark.asyncio
async def test_fabricator_failure_raises_agent_execution_error() -> None:
    """Si ApiFabricatorAgent falla → AgentExecutionError (no improvisa)."""
    mission_id = "m-fail"
    mission = _mission(mission_id)
    bp = _blueprint_dict(mission_id)
    bp["modules"][0]["external_apis"] = ["unknown_service"]
    bp_yaml = yaml.dump(bp)
    map_yaml = yaml.dump(_map_dict(mission_id))

    fabricator = AsyncMock()
    fabricator.generate_connector = AsyncMock(side_effect=RuntimeError("service unreachable"))

    with (
        patch("agents.iron_coder.read_file", return_value=bp_yaml),
        patch("agents.iron_coder.write_file"),
        patch("tools.map_tools.read_file", return_value=map_yaml),
        patch("tools.map_tools.write_file"),
    ):
        agent = _make_agent(_mock_llm(), fabricator)
        with pytest.raises(AgentExecutionError) as exc_info:
            await agent.run(mission)

    assert "ApiFabricator falló" in str(exc_info.value)
    assert exc_info.value.agent == AgentRole.IRON_CODER


@pytest.mark.asyncio
async def test_all_writes_use_file_tools() -> None:
    """Todos los writes usan file_tools.write_file — mock verifica cero open() directo."""
    mission_id = "m-wt"
    mission = _mission(mission_id)
    bp_yaml = yaml.dump(_blueprint_dict(mission_id))
    map_yaml = yaml.dump(_map_dict(mission_id))

    with (
        patch("agents.iron_coder.read_file", return_value=bp_yaml) as _,
        patch("agents.iron_coder.write_file") as mock_ft_write,
        patch("tools.map_tools.read_file", return_value=map_yaml),
        patch("tools.map_tools.write_file"),
        patch("builtins.open") as mock_open,
    ):
        agent = _make_agent(_mock_llm("# code\n"))
        await agent.run(mission)

    mock_ft_write.assert_called()
    mock_open.assert_not_called()


@pytest.mark.asyncio
async def test_map_updated_after_module_creation() -> None:
    """MAP.yaml actualizado con status=created tras generar módulo."""
    mission_id = "m-map"
    mission = _mission(mission_id)
    bp_yaml = yaml.dump(_blueprint_dict(mission_id))
    map_yaml = yaml.dump(_map_dict(mission_id))
    written_maps: list[str] = []

    def capture_map_write(path: str, content: str) -> None:
        if "MAP.yaml" in path:
            written_maps.append(content)

    with (
        patch("agents.iron_coder.read_file", return_value=bp_yaml),
        patch("agents.iron_coder.write_file"),
        patch("tools.map_tools.read_file", return_value=map_yaml),
        patch("tools.map_tools.write_file", side_effect=capture_map_write),
    ):
        agent = _make_agent(_mock_llm("# code\nline2\n"))
        await agent.run(mission)

    assert written_maps, "MAP.yaml nunca fue escrito"
    saved = yaml.safe_load(written_maps[-1])
    entry = saved["files"][0]
    assert entry["status"] == "created"
    assert entry["line_count"] is not None


@pytest.mark.asyncio
async def test_root_jail_violation_propagates() -> None:
    """RootJailViolationError propagada si file_tools la lanza."""
    mission_id = "m-jail"
    mission = _mission(mission_id)
    bp_yaml = yaml.dump(_blueprint_dict(mission_id))

    with (
        patch("agents.iron_coder.read_file", return_value=bp_yaml),
        patch(
            "agents.iron_coder.write_file",
            side_effect=RootJailViolationError("escape attempt"),
        ),
        patch("tools.map_tools.read_file", return_value=yaml.dump(_map_dict(mission_id))),
        patch("tools.map_tools.write_file"),
    ):
        agent = _make_agent(_mock_llm("# code\n"))
        with pytest.raises(RootJailViolationError):
            await agent.run(mission)
