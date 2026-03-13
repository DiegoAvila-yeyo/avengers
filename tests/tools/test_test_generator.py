"""tests/tools/test_test_generator.py — Suite QA para tools/test_generator.py.

Valida:
- generate_tests produce archivos solo para AC con automated=True (Widow).
- Hulk: divide en _part1/_part2 cuando el contenido supera MAX_TEST_LINES.
- Los archivos se registran en MAP.yaml (CAP'S MAP).
- run_tests_with_coverage retorna el resumen correcto.
- Ruta vacía / sin criterios devuelve lista vacía.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core.blueprint_schema import AcceptanceCriterion, BlueprintV1, FileEntry
from core.models import AgentRole
from tools.test_generator import (
    MAX_TEST_LINES,
    _build_module,
    _render_block,
    _split,
    generate_tests,
    run_tests_with_coverage,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_ac(ac_id: str, *, automated: bool = True) -> AcceptanceCriterion:
    return AcceptanceCriterion(id=ac_id, description=f"Desc {ac_id}", automated=automated)


def _make_blueprint(criteria: list[AcceptanceCriterion]) -> BlueprintV1:
    return BlueprintV1(
        blueprint_id="bp-test-01",
        mission_id="mission-test-01",
        product_name="TestProduct",
        problem_statement="test",
        target_audience="QA",
        tech_stack=["python"],
        modules=[],
        data_models=[],
        api_endpoints=[],
        acceptance_criteria=criteria,
    )


# ── _render_block ─────────────────────────────────────────────────────────────


def test_render_block_contains_ac_id() -> None:
    ac = _make_ac("AC-001")
    block = _render_block(ac)
    assert "test_ac_001" in block
    assert "[AC-001]" in block


def test_render_block_safe_id_replaces_dashes() -> None:
    ac = _make_ac("AC-042")
    assert "test_ac_042" in _render_block(ac)


# ── _build_module ─────────────────────────────────────────────────────────────


def test_build_module_includes_header() -> None:
    content = _build_module([_make_ac("AC-001")], "MyProduct")
    assert "MyProduct" in content
    assert "from __future__ import annotations" in content


def test_build_module_renders_all_criteria() -> None:
    criteria = [_make_ac(f"AC-{i:03d}") for i in range(5)]
    content = _build_module(criteria, "Prod")
    for i in range(5):
        assert f"AC-{i:03d}" in content


# ── _split ────────────────────────────────────────────────────────────────────


def test_split_returns_single_chunk_for_small_input() -> None:
    criteria = [_make_ac(f"AC-{i:03d}") for i in range(3)]
    chunks = _split(criteria)
    assert len(chunks) == 1
    assert chunks[0] == criteria


def test_split_divides_large_input() -> None:
    criteria = [_make_ac(f"AC-{i:03d}") for i in range(MAX_TEST_LINES)]  # very large
    chunks = _split(criteria)
    assert len(chunks) > 1
    assert all(len(c) <= MAX_TEST_LINES // 10 for c in chunks)


# ── generate_tests — Protocolo Widow ─────────────────────────────────────────


def test_generate_tests_skips_non_automated(tmp_path: Path) -> None:
    criteria = [_make_ac("AC-001", automated=False), _make_ac("AC-002", automated=False)]
    bp = _make_blueprint(criteria)
    with patch("tools.test_generator.write_file"), patch("tools.test_generator.add_file_entry"):
        result = generate_tests(bp, "missions/test/MAP.yaml")
    assert result == []


def test_generate_tests_only_automated_ac(tmp_path: Path) -> None:
    criteria = [_make_ac("AC-001", automated=True), _make_ac("AC-002", automated=False)]
    bp = _make_blueprint(criteria)

    written_content: list[str] = []

    def fake_write(path: str, content: str) -> Path:
        written_content.append(content)
        return Path(path)

    with patch("tools.test_generator.write_file", side_effect=fake_write), \
         patch("tools.test_generator.add_file_entry"):
        result = generate_tests(bp, "missions/test/MAP.yaml")

    assert len(result) == 1
    assert "AC-001" in written_content[0]
    assert "AC-002" not in written_content[0]


# ── generate_tests — Protocolo Hulk ──────────────────────────────────────────


def test_generate_tests_hulk_splits_large_blueprint() -> None:
    # 55 criteria * ~6 lines/block ≈ 334 lines > MAX_TEST_LINES=300 → split
    criteria = [_make_ac(f"AC-{i:03d}") for i in range(55)]
    bp = _make_blueprint(criteria)

    written_paths: list[str] = []

    def fake_write(path: str, content: str) -> Path:
        written_paths.append(path)
        return Path(path)

    with patch("tools.test_generator.write_file", side_effect=fake_write), \
         patch("tools.test_generator.add_file_entry"):
        result = generate_tests(bp, "missions/test/MAP.yaml")

    assert len(result) > 1
    assert all("_part" in p for p in result)


# ── generate_tests — CAP'S MAP registration ───────────────────────────────────


def test_generate_tests_registers_in_map() -> None:
    criteria = [_make_ac("AC-001")]
    bp = _make_blueprint(criteria)

    add_mock = MagicMock()
    with patch("tools.test_generator.write_file", return_value=Path("x")), \
         patch("tools.test_generator.add_file_entry", add_mock):
        generate_tests(bp, "missions/test/MAP.yaml")

    assert add_mock.called
    entry: FileEntry = add_mock.call_args[0][1]
    assert entry.created_by == AgentRole.IRON_CODER
    assert entry.status == "created"
    assert entry.module == "__test_generator__"


# ── run_tests_with_coverage ───────────────────────────────────────────────────


async def test_run_tests_empty_paths_returns_defaults() -> None:
    result = await run_tests_with_coverage([])
    assert result["returncode"] == 0
    assert result["coverage_pct"] == 100.0


async def test_run_tests_parses_coverage_json() -> None:
    coverage_data = json.dumps({"totals": {"percent_covered": 87.5}})
    with patch("tools.test_generator.run_command", new_callable=AsyncMock) as mock_cmd, \
         patch("tools.test_generator.read_file", return_value=coverage_data):
        mock_cmd.return_value = (0, "1 passed", "")
        result = await run_tests_with_coverage(["tests/generated/test_bp.py"])

    assert result["coverage_pct"] == 87.5
    assert result["returncode"] == 0


async def test_run_tests_handles_missing_coverage_file() -> None:
    with patch("tools.test_generator.run_command", new_callable=AsyncMock) as mock_cmd, \
         patch("tools.test_generator.read_file", side_effect=FileNotFoundError):
        mock_cmd.return_value = (1, "2 failed", "")
        result = await run_tests_with_coverage(["tests/generated/test_bp.py"])

    assert result["coverage_pct"] == 0.0
    assert result["returncode"] == 1
