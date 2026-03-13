"""tests/agents/test_black_widow.py — Suite de tests para BlackWidowAgent.

Cobertura: run() procesa violaciones, _split_file, _fix_imports,
WidowReport persistido, MAP actualizado, y tests no eliminados.
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

from datetime import datetime, timezone

from agents.black_widow import BlackWidowAgent  # noqa: E402
from agents.hulk import GuardrailReport, GuardrailViolation, ViolationType  # noqa: E402
from core.models import Mission  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def llm_mock() -> MagicMock:
    mock = MagicMock()
    mock.complete = AsyncMock(return_value=MagicMock(content="# fixed code\n"))
    return mock


@pytest.fixture
def widow(llm_mock: MagicMock) -> BlackWidowAgent:
    return BlackWidowAgent(llm_client=llm_mock, project_root=PROJECT_ROOT)


def _make_report(mission_id: str, violations: list[GuardrailViolation]) -> GuardrailReport:
    return GuardrailReport(
        mission_id=mission_id,
        scanned_files=1,
        violations=violations,
        passed=len(violations) == 0,
        generated_at=datetime.now(timezone.utc),  # noqa: UP017
    )


# ── Test 1: run() procesa todas las violaciones del GuardrailReport ──────────

@pytest.mark.asyncio
async def test_run_processes_all_violations(widow: BlackWidowAgent) -> None:
    mission = Mission(mission_id="mission-w01")
    violations = [
        GuardrailViolation(file_path="output/big.py", violation_type=ViolationType.LINE_LIMIT,
                           detail="301 lines", severity="error"),
        GuardrailViolation(
            file_path="output/imports.py", violation_type=ViolationType.UNUSED_IMPORT,
            detail="import os", severity="warning"),
    ]
    report = _make_report("mission-w01", violations)
    report_yaml = yaml.dump(report.model_dump(mode="json"), allow_unicode=True)

    written: dict[str, str] = {}

    with (
        patch("agents.black_widow.read_file", return_value=report_yaml),
        patch("agents.black_widow.write_file", side_effect=lambda p, c: written.update({p: c})),
        patch("agents.black_widow.run_command", new_callable=AsyncMock, return_value=(0, "[]", "")),
        patch("agents.black_widow.resolve_safe_path", return_value=Path("/tmp/f.py")),
        patch(
            "tools.code_splitter.split_file_semantically",
            new_callable=AsyncMock, return_value=[]),
        patch(
            "agents.black_widow.BlackWidowAgent._split_file",
            new_callable=AsyncMock, return_value=[]),
    ):
        result = await widow.run(mission)

    assert result.mission_id == "mission-w01"
    assert any("widow_report" in k for k in written)


# ── Test 2: _split_file delega en code_splitter y retorna lista de rutas ─────

@pytest.mark.asyncio
async def test_split_file_produces_files_under_limit(widow: BlackWidowAgent) -> None:
    content = "\n".join(["x = 1"] * 310)
    new_files = ["output/big_models.py", "output/big_utils.py"]

    with (
        patch("agents.black_widow.read_file", return_value=content),
        patch("tools.code_splitter.split_file_semantically",
              new_callable=AsyncMock, return_value=new_files),
    ):
        result = await widow._split_file("output/big.py", "mission-w02")

    assert result == new_files


# ── Test 3: _fix_imports usa ruff F401 --fix (shell_tools mock) ──────────────

@pytest.mark.asyncio
async def test_fix_imports_uses_ruff(widow: BlackWidowAgent) -> None:
    ruff_output = '[{"message": "unused import os", "location": {"row": 1}}]'
    with (
        patch("agents.black_widow.run_command",
              new_callable=AsyncMock, return_value=(0, ruff_output, "")),
        patch("agents.black_widow.resolve_safe_path", return_value=Path("/tmp/f.py")),
    ):
        count = await widow._fix_imports("output/file.py")

    assert count == 1


# ── Test 4: WidowReport guardado en missions/{id}/widow_report.yaml ──────────

@pytest.mark.asyncio
async def test_widow_report_saved(widow: BlackWidowAgent) -> None:
    mission = Mission(mission_id="mission-w04")
    report = _make_report("mission-w04", [])
    report_yaml = yaml.dump(report.model_dump(mode="json"), allow_unicode=True)

    written_paths: list[str] = []
    with (
        patch("agents.black_widow.read_file", return_value=report_yaml),
        patch(
            "agents.black_widow.write_file",
            side_effect=lambda p, c: written_paths.append(str(p))),
    ):
        await widow.run(mission)

    assert any("mission-w04/widow_report.yaml" in p for p in written_paths)


# ── Test 5: MAP.yaml actualizado si hubo splits ───────────────────────────────

@pytest.mark.asyncio
async def test_map_updated_after_split(widow: BlackWidowAgent) -> None:
    mission = Mission(mission_id="mission-w05")
    violations = [
        GuardrailViolation(file_path="output/fat.py", violation_type=ViolationType.LINE_LIMIT,
                           detail="350 lines", severity="error"),
    ]
    report = _make_report("mission-w05", violations)
    report_yaml = yaml.dump(report.model_dump(mode="json"), allow_unicode=True)
    map_yaml = yaml.dump({"files": [{"path": "output/fat.py", "status": "created"}]})
    new_files = ["output/fat_models.py", "output/fat_utils.py"]

    written: dict[str, str] = {}

    def _read_side(path: str) -> str:
        if "hulk_report" in path:
            return report_yaml
        if "MAP.yaml" in path:
            return map_yaml
        return "\n".join(["x = 1"] * 310)

    with (
        patch("agents.black_widow.read_file", side_effect=_read_side),
        patch(
            "agents.black_widow.write_file",
            side_effect=lambda p, c: written.update({str(p): c})),
        patch("agents.black_widow.BlackWidowAgent._split_file",
              new_callable=AsyncMock, return_value=new_files),
    ):
        await widow.run(mission)

    assert any("MAP.yaml" in k for k in written)
    saved_map = yaml.safe_load(list(v for k, v in written.items() if "MAP.yaml" in k)[0])
    paths = [f["path"] for f in saved_map["files"]]
    assert "output/fat_models.py" in paths
    assert "output/fat_utils.py" in paths


# ── Test 6: Widow NO modifica archivos de test ────────────────────────────────

@pytest.mark.asyncio
async def test_does_not_delete_test_files(widow: BlackWidowAgent) -> None:
    mission = Mission(mission_id="mission-w06")
    violations = [
        GuardrailViolation(file_path="tests/agents/test_something.py",
                           violation_type=ViolationType.LINE_LIMIT,
                           detail="350 lines", severity="error"),
    ]
    report = _make_report("mission-w06", violations)
    report_yaml = yaml.dump(report.model_dump(mode="json"), allow_unicode=True)

    written: dict[str, str] = {}
    with (
        patch("agents.black_widow.read_file", return_value=report_yaml),
        patch(
            "agents.black_widow.write_file",
            side_effect=lambda p, c: written.update({str(p): c})),
    ):
        await widow.run(mission)

    # Only widow_report should be written — test file must NOT be modified
    assert all("test_something.py" not in k for k in written)
    assert any("widow_report" in k for k in written)
