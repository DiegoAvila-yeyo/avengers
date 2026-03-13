"""tests/agents/test_hulk.py — Suite de tests para HulkAgent.

Cobertura: detección de line_limit, patrones prohibidos, archivo limpio,
lanzamiento de HulkViolationError, paso con sólo warnings, y persistencia del reporte.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

os.environ.setdefault("OPENAI_API_KEY", "sk-test-openai-key-for-tests")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-anthropic-key-for-tests")
os.environ.setdefault("REDDIT_CLIENT_ID", "test-reddit-id-abc123")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "test-reddit-secret-abc123")
os.environ.setdefault("X_API_KEY", "test-x-api-key-abc123")
os.environ.setdefault("X_API_SECRET", "test-x-api-secret-abc123")
os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017/avengers_test")

from agents.hulk import HulkAgent, ViolationType  # noqa: E402
from core.exceptions import HulkViolationError  # noqa: E402
from core.models import Mission  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def hulk() -> HulkAgent:
    return HulkAgent(project_root=PROJECT_ROOT)


# ── Test 1: detecta archivo > 300 líneas ─────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_detects_line_limit_violation(hulk: HulkAgent) -> None:
    big_content = "\n".join(["x = 1"] * 301)
    with (
        patch("agents.hulk.read_file", return_value=big_content),
        patch("agents.hulk.run_command", new_callable=AsyncMock, return_value=(0, "[]", "")),
        patch("agents.hulk.resolve_safe_path", return_value=Path("/tmp/big.py")),
    ):
        violations = await hulk.scan_file("output/big_file.py")

    line_violations = [v for v in violations if v.violation_type == ViolationType.LINE_LIMIT]
    assert len(line_violations) == 1
    assert line_violations[0].severity == "error"
    assert line_violations[0].line_number == 301


# ── Test 2: detecta open() como patrón prohibido ─────────────────────────────

@pytest.mark.asyncio
async def test_scan_detects_forbidden_open(hulk: HulkAgent) -> None:
    content = 'with open("file.txt") as f:\n    data = f.read()\n'
    with (
        patch("agents.hulk.read_file", return_value=content),
        patch("agents.hulk.run_command", new_callable=AsyncMock, return_value=(0, "[]", "")),
        patch("agents.hulk.resolve_safe_path", return_value=Path("/tmp/bad.py")),
    ):
        violations = await hulk.scan_file("output/bad_file.py")

    forbidden = [v for v in violations if v.violation_type == ViolationType.FORBIDDEN_PATTERN]
    assert len(forbidden) >= 1
    assert forbidden[0].severity == "error"


# ── Test 3: archivo limpio → lista vacía ─────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_clean_file_returns_no_violations(hulk: HulkAgent) -> None:
    clean_content = (
        "from tools.file_tools import read_file\n\n"
        "def hello() -> str:\n    return 'hello'\n"
    )
    with (
        patch("agents.hulk.read_file", return_value=clean_content),
        patch("agents.hulk.run_command", new_callable=AsyncMock, return_value=(0, "[]", "")),
        patch("agents.hulk.resolve_safe_path", return_value=Path("/tmp/clean.py")),
    ):
        violations = await hulk.scan_file("output/clean_file.py")

    assert violations == []


# ── Test 4: run() lanza HulkViolationError si hay errores ────────────────────

@pytest.mark.asyncio
async def test_run_raises_on_errors(hulk: HulkAgent) -> None:
    mission = Mission(mission_id="mission-test01")
    map_yaml = yaml.dump({
        "files": [{"path": "output/bad.py", "status": "created"}]
    })

    big_content = "\n".join(["x = 1"] * 301)

    def _side_effect(p: str) -> str:
        return map_yaml if "MAP" in p else big_content

    with (
        patch("agents.hulk.read_file", side_effect=_side_effect),
        patch("agents.hulk.write_file"),
        patch("agents.hulk.run_command", new_callable=AsyncMock, return_value=(0, "[]", "")),
        patch("agents.hulk.resolve_safe_path", return_value=Path("/tmp/bad.py")),
        pytest.raises(HulkViolationError) as exc_info,
    ):
        await hulk.run(mission)

    assert exc_info.value.error_count >= 1
    assert exc_info.value.mission_id == "mission-test01"


# ── Test 5: run() no lanza si solo hay warnings ───────────────────────────────

@pytest.mark.asyncio
async def test_run_passes_with_only_warnings(hulk: HulkAgent) -> None:
    mission = Mission(mission_id="mission-test02")
    map_yaml = yaml.dump({
        "files": [{"path": "output/warn.py", "status": "created"}]
    })
    # Ruff returns an unused import warning (F401)
    ruff_output = '[{"message": "unused import os", "location": {"row": 1}}]'
    clean_content = "import os\n\ndef hello() -> str:\n    return 'hi'\n"

    def _side_effect2(p: str) -> str:
        return map_yaml if "MAP" in p else clean_content

    with (
        patch("agents.hulk.read_file", side_effect=_side_effect2),
        patch("agents.hulk.write_file"),
        patch(
            "agents.hulk.run_command",
            new_callable=AsyncMock,
            return_value=(0, ruff_output, ""),
        ),
        patch("agents.hulk.resolve_safe_path", return_value=Path("/tmp/warn.py")),
    ):
        result = await hulk.run(mission)

    assert result.mission_id == "mission-test02"


# ── Test 6: reporte guardado en missions/{id}/hulk_report.yaml ───────────────

@pytest.mark.asyncio
async def test_report_saved_to_correct_path(hulk: HulkAgent) -> None:
    mission = Mission(mission_id="mission-test03")
    map_yaml = yaml.dump({"files": []})

    written_paths: list[str] = []

    def capture_write(path: str, content: str) -> None:
        written_paths.append(str(path))

    with (
        patch("agents.hulk.read_file", return_value=map_yaml),
        patch("agents.hulk.write_file", side_effect=capture_write),
    ):
        await hulk.run(mission)

    assert any("mission-test03/hulk_report.yaml" in p for p in written_paths)
