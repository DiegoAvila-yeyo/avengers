"""tests/tools/test_qa_runner.py — Tests para QARunner."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.models import Mission
from tools.qa_runner import CoverageReport, QAReport, QARunner, TestResult

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_coverage(total: float = 85.0, meets: bool = True) -> CoverageReport:
    return CoverageReport(
        total_coverage=total,
        per_file={"core/models.py": total},
        uncovered_lines={"core/models.py": []},
        meets_threshold=meets,
    )


def _make_report(passed: int = 5, failed: int = 0, total_cov: float = 85.0) -> QAReport:
    meets = total_cov >= 80.0
    return QAReport(
        mission_id="mission-test",
        total_tests=passed + failed,
        passed=passed,
        failed=failed,
        errors=0,
        duration_seconds=1.5,
        coverage=_make_coverage(total_cov, meets),
        test_results=[
            TestResult(test_id="tests/test_foo.py::test_bar", passed=True, duration_ms=10.0)
        ],
        generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )


# ── Test 1: run_suite ejecuta pytest con cobertura ────────────────────────────


async def test_run_suite_executes_pytest_with_coverage(tmp_path: Path) -> None:
    """run_suite debe llamar run_command con pytest y --cov."""
    mission = Mission(mission_id="m-001")
    runner = QARunner(project_root=tmp_path)

    pytest_stdout = "5 passed in 1.23s"
    fake_cov = {
        "totals": {"percent_covered": 88.0},
        "files": {"core/models.py": {"summary": {"percent_covered": 88.0}, "missing_lines": []}},
    }
    (tmp_path / "coverage.json").write_text(json.dumps(fake_cov))
    (tmp_path / "missions" / "m-001").mkdir(parents=True, exist_ok=True)

    with patch(
        "tools.qa_runner.run_command", new=AsyncMock(return_value=(0, pytest_stdout, ""))
    ) as mock_cmd:
        report = await runner.run_suite(mission, ["tests/"])

    called_cmd = mock_cmd.call_args[0][0]
    assert called_cmd[0] == "pytest"
    assert any("--cov" in arg for arg in called_cmd)
    assert report.mission_id == "m-001"
    assert report.coverage.total_coverage == 88.0


# ── Test 2: check_threshold falla si cobertura < 80% ─────────────────────────


async def test_check_threshold_fails_below_80(tmp_path: Path) -> None:
    runner = QARunner(project_root=tmp_path)
    report = _make_report(total_cov=71.4)
    result = await runner.check_threshold(report)
    assert result is False


# ── Test 3: check_threshold pasa si cobertura >= 80% ─────────────────────────


async def test_check_threshold_passes_above_80(tmp_path: Path) -> None:
    runner = QARunner(project_root=tmp_path)
    report = _make_report(total_cov=83.2)
    result = await runner.check_threshold(report)
    assert result is True


# ── Test 4: generate_summary incluye ✅/❌ según resultado ────────────────────


@pytest.mark.parametrize(
    "total_cov,failed,expected_icon",
    [
        (83.2, 0, "✅"),
        (71.4, 3, "❌"),
        (79.9, 0, "❌"),  # cov < 80% aunque no haya fallos
    ],
)
async def test_generate_summary_format(
    tmp_path: Path, total_cov: float, failed: int, expected_icon: str
) -> None:
    runner = QARunner(project_root=tmp_path)
    passed = max(0, 5 - failed)
    report = _make_report(passed=passed, failed=failed, total_cov=total_cov)
    summary = await runner.generate_summary(report)
    assert expected_icon in summary


# ── Test 5: QAReport guardado en missions/{id}/qa_report.yaml ─────────────────


async def test_qa_report_saved(tmp_path: Path) -> None:
    mission = Mission(mission_id="m-save")
    runner = QARunner(project_root=tmp_path)

    pytest_stdout = "3 passed in 0.5s"
    fake_cov = {"totals": {"percent_covered": 90.0}, "files": {}}
    (tmp_path / "coverage.json").write_text(json.dumps(fake_cov))

    saved_paths: list[str] = []

    def _capture_write(path: str, content: str) -> None:
        saved_paths.append(path)

    with (
        patch("tools.qa_runner.run_command", new=AsyncMock(return_value=(0, pytest_stdout, ""))),
        patch("tools.qa_runner.write_file", side_effect=_capture_write),
    ):
        await runner.run_suite(mission, ["tests/"])

    assert any("m-save/qa_report.yaml" in p for p in saved_paths), (
        f"qa_report.yaml no fue guardado en missions/m-save/. Paths: {saved_paths}"
    )
