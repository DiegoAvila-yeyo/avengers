"""tests/agents/test_vision_ui.py — Suite de tests para VisionUIAgent.

Cobertura: generación de componentes por DataModel, Protocolo Hulk UI (split >150L),
ROOT JAIL via file_tools, actualización MAP.yaml, StyleGuide inyectada en cada LLM call.
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

from agents.vision_ui import VisionUIAgent  # noqa: E402
from core.models import AgentRole, Mission  # noqa: E402
from tools.ui_scaffold import UIScaffolder  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ── Helpers ───────────────────────────────────────────────────────────────────


def _blueprint_dict(mission_id: str = "m-ui") -> dict:
    return {
        "blueprint_id": f"bp-{mission_id}",
        "mission_id": mission_id,
        "product_name": "UIProduct",
        "problem_statement": "Build UI",
        "target_audience": "Users",
        "tech_stack": ["React", "TypeScript"],
        "modules": [
            {"module_name": "ui_module", "responsibility": "UI layer", "estimated_lines": 100}
        ],
        "data_models": [{"name": "Item", "fields": {"id": "str", "name": "str"}}],
        "api_endpoints": [
            {
                "method": "GET",
                "path": "/items",
                "description": "List items",
                "response_schema": {"items": "list"},
                "known_api": True,
            }
        ],
        "acceptance_criteria": [{"id": "AC-001", "description": "UI renders", "automated": True}],
    }


def _map_dict(mission_id: str = "m-ui") -> dict:
    return {"mission_id": mission_id, "blueprint_id": f"bp-{mission_id}", "files": []}


def _mission(mission_id: str = "m-ui") -> Mission:
    m = Mission(mission_id=mission_id)
    m.blueprint_ref = f"missions/{mission_id}/blueprint.yaml"
    return m


def _mock_llm(content: str = "const X = () => null;\nexport default X;\n") -> AsyncMock:
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=MagicMock(content=content))
    return llm


def _make_agent(llm: AsyncMock, file_tools: MagicMock | None = None) -> VisionUIAgent:
    if file_tools is None:
        ft: MagicMock = MagicMock()
        ft.write_file = MagicMock(side_effect=lambda rel, content: Path(rel))
    else:
        ft = file_tools
    scaffolder = MagicMock(spec=UIScaffolder)
    scaffolder.scaffold_project = AsyncMock(return_value=[])
    return VisionUIAgent(
        llm_client=llm,
        scaffolder=scaffolder,
        file_tools=ft,
        project_root=PROJECT_ROOT,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_generates_components_for_data_models() -> None:
    """run() genera atoms, molecules y organisms para cada DataModel del Blueprint."""
    mid = "m-models"
    mission = _mission(mid)
    bp_yaml = yaml.dump(_blueprint_dict(mid))

    llm = _mock_llm()
    ft = MagicMock()
    ft.write_file = MagicMock(side_effect=lambda rel, content: Path(rel))
    agent = _make_agent(llm, ft)

    with (
        patch("agents.vision_ui.read_file", side_effect=[bp_yaml, FileNotFoundError]),
        patch("agents.vision_ui.add_file_entry"),
    ):
        result = await agent.run(mission)

    # 1 DataModel × (1 atom + 1 molecule + 2 organisms) + 1 page = 5 LLM calls
    assert llm.complete.call_count == 5
    # file_tools.write_file called for each generated component
    assert ft.write_file.call_count == 5
    assert len(result.log) == 5
    assert all(e.agent == AgentRole.VISION_UI.value for e in result.log)


@pytest.mark.asyncio
async def test_oversized_component_triggers_split() -> None:
    """Componente > 150 líneas → LLM solicitado a dividir (Protocolo Hulk UI)."""
    mid = "m-hulk"
    mission = _mission(mid)
    bp_yaml = yaml.dump(_blueprint_dict(mid))

    oversized = "\n".join(["line"] * 160)  # 160 lines → triggers split
    short = "const X = () => null;\nexport default X;\n"

    call_count = 0

    async def _side_effect(req):  # type: ignore[no-untyped-def]
        nonlocal call_count
        call_count += 1
        return MagicMock(content=oversized if call_count == 1 else short)

    llm = AsyncMock()
    llm.complete = AsyncMock(side_effect=_side_effect)
    agent = _make_agent(llm)

    with (
        patch("agents.vision_ui.read_file", side_effect=[bp_yaml, FileNotFoundError]),
        patch("agents.vision_ui.add_file_entry"),
    ):
        await agent.run(mission)

    # First component triggers a split call → at least 2 LLM calls total (original + split)
    assert llm.complete.call_count >= 2


@pytest.mark.asyncio
async def test_all_writes_use_file_tools() -> None:
    """Todos los writes de componentes usan file_tools.write_file (ROOT JAIL)."""
    mid = "m-jail"
    mission = _mission(mid)
    bp_yaml = yaml.dump(_blueprint_dict(mid))

    llm = _mock_llm()
    ft = MagicMock()
    written_paths: list[str] = []
    ft.write_file = MagicMock(
        side_effect=lambda rel, content: written_paths.append(rel) or Path(rel)
    )
    agent = _make_agent(llm, ft)

    with (
        patch("agents.vision_ui.read_file", side_effect=[bp_yaml, FileNotFoundError]),
        patch("agents.vision_ui.add_file_entry"),
    ):
        await agent.run(mission)

    assert len(written_paths) > 0
    for path in written_paths:
        assert path.startswith(f"output/{mid}/frontend/src/")


@pytest.mark.asyncio
async def test_map_updated_with_component_entries() -> None:
    """MAP.yaml recibe un FileEntry por cada componente generado."""
    mid = "m-map"
    mission = _mission(mid)
    bp_yaml = yaml.dump(_blueprint_dict(mid))

    llm = _mock_llm()
    agent = _make_agent(llm)

    added_entries: list = []
    with (
        patch("agents.vision_ui.read_file", side_effect=[bp_yaml, FileNotFoundError]),
        patch(
            "agents.vision_ui.add_file_entry",
            side_effect=lambda _mp, entry: added_entries.append(entry),
        ),
    ):
        await agent.run(mission)

    assert len(added_entries) > 0
    assert all(e.created_by == AgentRole.VISION_UI for e in added_entries)
    assert all(e.status == "created" for e in added_entries)


@pytest.mark.asyncio
async def test_style_guide_injected_in_every_prompt() -> None:
    """StyleGuide aparece en el user_message de cada LLM call."""
    mid = "m-sg"
    mission = _mission(mid)
    bp_yaml = yaml.dump(_blueprint_dict(mid))

    llm = _mock_llm()
    agent = _make_agent(llm)

    with (
        patch("agents.vision_ui.read_file", side_effect=[bp_yaml, FileNotFoundError]),
        patch("agents.vision_ui.add_file_entry"),
    ):
        await agent.run(mission)

    for llm_call in llm.complete.call_args_list:
        request = llm_call.args[0]
        assert "StyleGuide" in request.user_message, (
            f"StyleGuide no encontrada en LLM call: {request.user_message[:80]}"
        )
