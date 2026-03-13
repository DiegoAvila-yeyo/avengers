"""tests/core/test_blueprint_schema.py — Tests para BlueprintV1 y MissionMap."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from core.blueprint_schema import (
    ApiEndpoint,
    BlueprintV1,
    FileEntry,
    MissionMap,
    ModuleSpec,
)
from core.models import AgentRole

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _valid_module(name: str = "auth_service", lines: int = 150) -> ModuleSpec:
    return ModuleSpec(
        module_name=name,
        responsibility="Handle authentication",
        estimated_lines=lines,
    )


def _minimal_blueprint(**overrides) -> BlueprintV1:
    defaults: dict = {
        "blueprint_id": "bp-001",
        "mission_id": "mission-abc",
        "product_name": "AvengersApp",
        "problem_statement": "Pain detected by Thor",
        "target_audience": "Developers",
        "tech_stack": ["Python", "FastAPI"],
        "modules": [_valid_module()],
        "data_models": [],
        "api_endpoints": [],
        "acceptance_criteria": [],
        "created_at": datetime.now(tz=timezone.utc)  # noqa: UP017,
    }
    defaults.update(overrides)
    return BlueprintV1(**defaults)


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_blueprint_rejects_module_over_300_lines():
    """BlueprintV1 con módulo de 301L → ValidationError (Protocolo Hulk enforced)."""
    with pytest.raises(ValidationError, match="Protocolo Hulk"):
        _minimal_blueprint(modules=[_valid_module(lines=301)])


def test_blueprint_is_immutable():
    """BlueprintV1 frozen → no permite mutación post-creación."""
    bp = _minimal_blueprint()
    with pytest.raises((ValidationError, TypeError)):
        bp.product_name = "HackedName"  # type: ignore[misc]


def test_mission_map_get_files_by_agent():
    """MissionMap.get_files_by_agent filtra correctamente por agente."""
    now = datetime.now(tz=timezone.utc)  # noqa: UP017
    iron_file = FileEntry(
        path="agents/iron_coder.py",
        created_by=AgentRole.IRON_CODER,
        module="iron_coder",
        responsibility="Generate code",
    )
    widow_file = FileEntry(
        path="agents/black_widow.py",
        created_by=AgentRole.BLACK_WIDOW,
        module="black_widow",
        responsibility="Refactor code",
    )
    mission_map = MissionMap(
        mission_id="m-1",
        blueprint_id="bp-1",
        files=[iron_file, widow_file],
        created_at=now,
        updated_at=now,
    )

    iron_files = mission_map.get_files_by_agent(AgentRole.IRON_CODER)
    assert len(iron_files) == 1
    assert iron_files[0].path == "agents/iron_coder.py"

    widow_files = mission_map.get_files_by_agent(AgentRole.BLACK_WIDOW)
    assert len(widow_files) == 1

    assert mission_map.get_files_by_agent(AgentRole.THOR) == []


def test_unknown_api_endpoint_serializes():
    """ApiEndpoint.known_api=False serializa correctamente (señal para API-Fabricator)."""
    endpoint = ApiEndpoint(
        method="GET",
        path="/external/data",
        description="Fetches data from unknown external API",
        response_schema={"data": "list"},
        known_api=False,
    )
    data = endpoint.model_dump()
    assert data["known_api"] is False
    assert data["method"] == "GET"


def test_mission_map_serializable_to_dict():
    """MissionMap es serializable a dict para exportación YAML / MongoDB."""
    now = datetime.now(tz=timezone.utc)  # noqa: UP017
    entry = FileEntry(
        path="core/models.py",
        created_by=AgentRole.CAPTAIN_AMERICA,
        module="core",
        responsibility="Domain models",
    )
    mission_map = MissionMap(
        mission_id="m-2",
        blueprint_id="bp-2",
        files=[entry],
        created_at=now,
        updated_at=now,
    )

    result = mission_map.model_dump()
    assert isinstance(result, dict)
    assert result["mission_id"] == "m-2"
    assert isinstance(result["files"], list)
    assert result["files"][0]["created_by"] == AgentRole.CAPTAIN_AMERICA


def test_mission_map_get_files_by_module():
    """MissionMap.get_files_by_module filtra correctamente por módulo."""
    now = datetime.now(tz=timezone.utc)  # noqa: UP017
    f1 = FileEntry(
        path="core/auth.py",
        created_by=AgentRole.IRON_CODER,
        module="auth",
        responsibility="Auth logic",
    )
    f2 = FileEntry(
        path="core/users.py",
        created_by=AgentRole.IRON_CODER,
        module="users",
        responsibility="User management",
    )
    mission_map = MissionMap(
        mission_id="m-3",
        blueprint_id="bp-3",
        files=[f1, f2],
        created_at=now,
        updated_at=now,
    )

    auth_files = mission_map.get_files_by_module("auth")
    assert len(auth_files) == 1
    assert auth_files[0].path == "core/auth.py"
    assert mission_map.get_files_by_module("nonexistent") == []
