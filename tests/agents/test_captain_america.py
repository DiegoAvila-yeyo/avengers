"""tests/agents/test_captain_america.py — Suite de tests para CaptainAmericaAgent.

Cobertura: generación de blueprint.yaml + MAP.yaml, reintentos Hulk,
AgentExecutionError al agotar reintentos, entradas pending en el MAP.
"""

from __future__ import annotations

import json
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

from agents.captain_america import CaptainAmericaAgent  # noqa: E402
from core.blueprint_schema import BlueprintV1, MissionMap  # noqa: E402
from core.exceptions import AgentExecutionError  # noqa: E402
from core.models import AgentRole, Mission  # noqa: E402, I001

# ── Helpers ───────────────────────────────────────────────────────────────────


def _valid_blueprint_dict(mission_id: str = "mission-test") -> dict:
    return {
        "blueprint_id": f"bp-{mission_id}",
        "mission_id": mission_id,
        "product_name": "TestProduct",
        "problem_statement": "A test problem",
        "target_audience": "Developers",
        "tech_stack": ["Python", "FastAPI"],
        "modules": [
            {
                "module_name": "auth_module",
                "responsibility": "Handles auth",
                "estimated_lines": 150,
            },
            {
                "module_name": "user_module",
                "responsibility": "Manages users",
                "estimated_lines": 200,
            },
        ],
        "data_models": [{"name": "UserModel", "fields": {"id": "str", "email": "str"}}],
        "api_endpoints": [
            {
                "method": "GET",
                "path": "/users",
                "description": "List users",
                "response_schema": {"users": "list"},
            },
        ],
        "acceptance_criteria": [
            {"id": "AC-001", "description": "Users can login", "automated": True},
        ],
    }


def _valid_blueprint_json(mission_id: str = "mission-test") -> str:
    return json.dumps(_valid_blueprint_dict(mission_id))


def _hulk_violation_json(mission_id: str = "mission-test") -> str:
    data = _valid_blueprint_dict(mission_id)
    data["modules"][0]["estimated_lines"] = 400  # > 300 → Hulk violation
    return json.dumps(data)


def _mock_llm(content: str) -> AsyncMock:
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=MagicMock(content=content))
    return llm


def _make_agent(llm: AsyncMock, root: Path) -> CaptainAmericaAgent:
    return CaptainAmericaAgent(llm_client=llm, mission_root=root)


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_run_generates_blueprint_and_map(tmp_path: Path) -> None:
    """run() escribe blueprint.yaml y MAP.yaml válidos en missions/{id}/."""
    mission = Mission()
    brief_path = tmp_path / f"missions/{mission.mission_id}/brief.yaml"
    brief_path.parent.mkdir(parents=True)
    brief_path.write_text("mission_id: test\npain_points: []\n")
    mission.brief_ref = f"missions/{mission.mission_id}/brief.yaml"

    agent = _make_agent(_mock_llm(_valid_blueprint_json(mission.mission_id)), tmp_path)

    with patch("tools.file_tools.PROJECT_ROOT", tmp_path):
        result = await agent.run(mission)

    bp_path = tmp_path / f"missions/{mission.mission_id}/blueprint.yaml"
    map_path = tmp_path / f"missions/{mission.mission_id}/MAP.yaml"
    assert bp_path.exists(), "blueprint.yaml no creado"
    assert map_path.exists(), "MAP.yaml no creado"

    bp_data = yaml.safe_load(bp_path.read_text())
    assert bp_data["product_name"] == "TestProduct"
    assert result.blueprint_ref == f"missions/{mission.mission_id}/blueprint.yaml"


async def test_run_retries_on_hulk_violation(tmp_path: Path) -> None:
    """Si el LLM devuelve módulo > 300L, el agente reintenta con el error como feedback."""
    call_count = 0
    mission = Mission()

    async def mock_complete(request: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            content = _hulk_violation_json(mission.mission_id)
        else:
            content = _valid_blueprint_json(mission.mission_id)
        return MagicMock(content=content)

    brief_path = tmp_path / f"missions/{mission.mission_id}/brief.yaml"
    brief_path.parent.mkdir(parents=True)
    brief_path.write_text("pain_points: []\n")
    mission.brief_ref = f"missions/{mission.mission_id}/brief.yaml"

    llm = AsyncMock()
    llm.complete = mock_complete
    agent = _make_agent(llm, tmp_path)

    with patch("tools.file_tools.PROJECT_ROOT", tmp_path):
        result = await agent.run(mission)

    assert call_count == 2, f"Se esperaban 2 llamadas al LLM, se hicieron {call_count}"
    assert result.blueprint_ref is not None


async def test_run_raises_after_max_internal_retries(tmp_path: Path) -> None:
    """Si el LLM siempre falla, se lanza AgentExecutionError tras 3 intentos."""
    mission = Mission()
    brief_path = tmp_path / f"missions/{mission.mission_id}/brief.yaml"
    brief_path.parent.mkdir(parents=True)
    brief_path.write_text("pain_points: []\n")
    mission.brief_ref = f"missions/{mission.mission_id}/brief.yaml"

    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=MagicMock(content="NOT VALID JSON <<<"))
    agent = _make_agent(llm, tmp_path)

    with (
        patch("tools.file_tools.PROJECT_ROOT", tmp_path),
        pytest.raises(AgentExecutionError) as exc_info,
    ):
        await agent.run(mission)

    assert exc_info.value.agent == AgentRole.CAPTAIN_AMERICA
    assert llm.complete.await_count == 3  # 1 intento + 2 reintentos


def test_build_map_creates_pending_entries_for_all_modules(tmp_path: Path) -> None:
    """_build_map_from_blueprint() genera 3 FileEntry 'pending' por cada módulo."""
    agent = _make_agent(AsyncMock(), tmp_path)
    blueprint = BlueprintV1(**_valid_blueprint_dict())
    mission_map = agent._build_map_from_blueprint(blueprint)

    assert isinstance(mission_map, MissionMap)
    module_names = {m.module_name for m in blueprint.modules}

    for mod_name in module_names:
        entries = mission_map.get_files_by_module(mod_name)
        assert len(entries) == 3, (
            f"Módulo '{mod_name}' tiene {len(entries)} entradas, se esperaban 3"
        )
        paths = {e.path for e in entries}
        assert f"agents/{mod_name}.py" in paths
        assert f"tools/{mod_name}_tools.py" in paths
        assert f"tests/{mod_name}/test_{mod_name}.py" in paths
        assert all(e.status == "pending" for e in entries)


def test_unknown_api_endpoint_reflected_in_map(tmp_path: Path) -> None:
    """Endpoint con known_api=False genera FileEntry con module='__api_fabricator__'."""
    agent = _make_agent(AsyncMock(), tmp_path)
    data = _valid_blueprint_dict()
    data["api_endpoints"].append({
        "method": "POST",
        "path": "/stripe/charge",
        "description": "Charge via Stripe",
        "response_schema": {"status": "str"},
        "known_api": False,
    })
    blueprint = BlueprintV1(**data)
    mission_map = agent._build_map_from_blueprint(blueprint)

    api_fabricator_files = mission_map.get_files_by_module("__api_fabricator__")
    assert len(api_fabricator_files) == 1, "Se esperaba 1 entrada para __api_fabricator__"
    assert api_fabricator_files[0].created_by == AgentRole.API_FABRICATOR
    assert "stripe" in api_fabricator_files[0].path
    assert mission_map.has_unknown_apis()


async def test_blueprint_saved_in_correct_path(tmp_path: Path) -> None:
    """blueprint.yaml se guarda exactamente en missions/{mission_id}/blueprint.yaml."""
    mission = Mission()
    brief_path = tmp_path / f"missions/{mission.mission_id}/brief.yaml"
    brief_path.parent.mkdir(parents=True)
    brief_path.write_text("pain_points: []\n")
    mission.brief_ref = f"missions/{mission.mission_id}/brief.yaml"

    agent = _make_agent(_mock_llm(_valid_blueprint_json(mission.mission_id)), tmp_path)

    with patch("tools.file_tools.PROJECT_ROOT", tmp_path):
        result = await agent.run(mission)

    expected_path = tmp_path / f"missions/{mission.mission_id}/blueprint.yaml"
    assert expected_path.exists(), f"blueprint.yaml no encontrado en {expected_path}"
    assert result.blueprint_ref == f"missions/{mission.mission_id}/blueprint.yaml"

    bp_data = yaml.safe_load(expected_path.read_text())
    assert bp_data["mission_id"] == mission.mission_id
