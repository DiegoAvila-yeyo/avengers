"""tests/tools/test_ui_scaffold.py — Suite QA para tools/ui_scaffold.py.

Valida:
1. scaffold_project crea estructura Atomic Design completa.
2. Todos los writes usan file_tools (ROOT JAIL AMD-01).
3. generate_design_tokens produce CSS con variables :root.
4. generate_api_client genera un método por ApiEndpoint.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.blueprint_schema import ApiEndpoint, BlueprintV1
from tools.ui_scaffold import ATOMIC_STRUCTURE, StyleGuide, UIScaffolder

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_scaffolder() -> tuple[UIScaffolder, MagicMock]:
    mock_ft = MagicMock()
    mock_ft.write_file = MagicMock()
    scaffolder = UIScaffolder(file_tools=mock_ft)
    return scaffolder, mock_ft


def _make_blueprint(endpoints: list[ApiEndpoint] | None = None) -> BlueprintV1:
    return BlueprintV1(
        blueprint_id="bp-ui-01",
        mission_id="mission-ui-01",
        product_name="TestApp",
        problem_statement="test",
        target_audience="devs",
        tech_stack=["react", "typescript"],
        modules=[],
        data_models=[],
        api_endpoints=endpoints or [],
        acceptance_criteria=[],
    )


# ── Test 1: scaffold_project crea estructura Atomic Design completa ────────────


@pytest.mark.asyncio
async def test_scaffold_creates_atomic_structure() -> None:
    scaffolder, mock_ft = _make_scaffolder()
    created = await scaffolder.scaffold_project("m-01")

    written_paths = [c.args[0] for c in mock_ft.write_file.call_args_list]

    # Verifica que se crean componentes de cada capa no vacía
    for layer in ("atoms", "molecules", "organisms"):
        for name in ATOMIC_STRUCTURE[layer]:
            assert any(name in p for p in written_paths), (
                f"Missing component {name} in layer {layer}"
            )

    # Verifica archivos de estilos y lib
    assert any("tokens.css" in p for p in written_paths)
    assert any("globals.css" in p for p in written_paths)
    assert any("api.ts" in p for p in written_paths)
    assert any("index.tsx" in p for p in written_paths)
    assert len(created) > 0


# ── Test 2: todos los writes vía file_tools (ROOT JAIL) ───────────────────────


@pytest.mark.asyncio
async def test_scaffold_uses_file_tools_for_all_writes() -> None:
    scaffolder, mock_ft = _make_scaffolder()

    # Patch to ensure open() is never called directly
    with patch("builtins.open") as mock_open:
        await scaffolder.scaffold_project("m-02")
        mock_open.assert_not_called()

    assert mock_ft.write_file.called
    # Every call must go through file_tools.write_file
    for c in mock_ft.write_file.call_args_list:
        path_arg = c.args[0]
        assert isinstance(path_arg, str), "write_file must receive str path"


# ── Test 3: generate_design_tokens produce CSS con variables :root ─────────────


@pytest.mark.asyncio
async def test_generate_design_tokens_produces_css_variables() -> None:
    scaffolder, _ = _make_scaffolder()
    sg = StyleGuide(
        color_primary="#FF0000",
        color_secondary="#00FF00",
        spacing_base_px=4,
        font_body="Roboto",
    )
    css = await scaffolder.generate_design_tokens(sg)

    assert ":root {" in css
    assert "--color-primary: #FF0000;" in css
    assert "--color-secondary: #00FF00;" in css
    assert "--spacing-base: 4px;" in css
    assert "--font-body: 'Roboto', sans-serif;" in css
    assert css.strip().endswith("}")


# ── Test 4: generate_api_client genera un método por ApiEndpoint ───────────────


@pytest.mark.asyncio
async def test_api_client_has_method_per_endpoint() -> None:
    scaffolder, _ = _make_scaffolder()
    endpoints = [
        ApiEndpoint(method="GET", path="/users", description="List users", response_schema={}),
        ApiEndpoint(method="POST", path="/users", description="Create user", response_schema={}),
        ApiEndpoint(
            method="DELETE", path="/users/{id}", description="Delete user", response_schema={}
        ),
    ]
    blueprint = _make_blueprint(endpoints)
    ts = await scaffolder.generate_api_client(blueprint)

    assert "get_users" in ts
    assert "post_users" in ts
    assert "delete_users" in ts
    assert ts.count("export async function") == len(endpoints)
