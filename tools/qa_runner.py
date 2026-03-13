"""tools/qa_runner.py — QA Runner: pytest + cobertura → QAReport."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone  # noqa: UP017
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import BaseModel, computed_field

from core.models import Mission
from tools.file_tools import write_file
from tools.shell_tools import run_command

logger = logging.getLogger(__name__)

# ── Modelos ───────────────────────────────────────────────────────────────────


class TestResult(BaseModel):
    test_id: str
    passed: bool
    duration_ms: float
    error_message: str | None = None


class CoverageReport(BaseModel):
    total_coverage: float
    per_file: dict[str, float]
    uncovered_lines: dict[str, list[int]]
    meets_threshold: bool


class QAReport(BaseModel):
    mission_id: str
    total_tests: int
    passed: int
    failed: int
    errors: int
    duration_seconds: float
    coverage: CoverageReport
    test_results: list[TestResult]
    generated_at: datetime

    @computed_field
    @property
    def success_rate(self) -> float:
        return (self.passed / self.total_tests * 100) if self.total_tests > 0 else 0.0


# ── Runner ────────────────────────────────────────────────────────────────────


class QARunner:
    """Ejecuta la suite de tests y genera un QAReport con cobertura."""

    MIN_COVERAGE_THRESHOLD: ClassVar[float] = 80.0

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    async def run_suite(self, mission: Mission, test_paths: list[str]) -> QAReport:
        """Ejecuta pytest con --cov, parsea resultados y guarda QAReport."""
        cov_json = str(self._root / "coverage.json")
        _, stdout, stderr = await run_command(
            ["pytest", *test_paths, "--cov=.", f"--cov-report=json:{cov_json}", "--tb=short", "-q"],
            timeout=120.0,
        )
        test_results, passed, failed, errors, duration = _parse_pytest_output(stdout + stderr)
        report = QAReport(
            mission_id=mission.mission_id,
            total_tests=len(test_results),
            passed=passed,
            failed=failed,
            errors=errors,
            duration_seconds=duration,
            coverage=_parse_coverage_json(cov_json, self.MIN_COVERAGE_THRESHOLD),
            test_results=test_results[:50],
            generated_at=datetime.now(timezone.utc),  # noqa: UP017
        )
        out_path = f"missions/{mission.mission_id}/qa_report.yaml"
        write_file(out_path, yaml.dump(report.model_dump(mode="json"), allow_unicode=True))
        return report

    async def check_threshold(self, report: QAReport) -> bool:
        """True si la cobertura total >= MIN_COVERAGE_THRESHOLD."""
        meets = report.coverage.total_coverage >= self.MIN_COVERAGE_THRESHOLD
        if not meets:
            thr = self.MIN_COVERAGE_THRESHOLD
            below = [f for f, c in report.coverage.per_file.items() if c < thr]
            logger.warning("Cobertura %.1f%% < mínimo. Bajos: %s", report.coverage.total_coverage, below)  # noqa: E501
        return meets

    async def generate_summary(self, report: QAReport) -> str:
        """Genera texto legible para el StateLog y el Checkpoint humano."""
        cov = report.coverage.total_coverage
        if report.coverage.meets_threshold and report.failed == 0:
            return f"✅ QA PASS — {report.passed}/{report.total_tests} tests, {cov:.1f}% cobertura"
        thr = self.MIN_COVERAGE_THRESHOLD
        return f"❌ QA FAIL — {report.failed} tests fallidos, {cov:.1f}% cobertura (mínimo: {thr:.0f}%)"  # noqa: E501


# ── Helpers privados ─────────────────────────────────────────────────────────
def _parse_pytest_output(
    output: str,
) -> tuple[list[TestResult], int, int, int, float]:
    passed = failed = errors = 0
    duration = 0.0
    test_results: list[TestResult] = []

    summary_match = re.search(
        r"(?:(\d+) passed)?.*?(?:(\d+) failed)?.*?(?:(\d+) error)?.*?in ([\d.]+)s",
        output,
    )
    if summary_match:
        passed = int(summary_match.group(1) or 0)
        failed = int(summary_match.group(2) or 0)
        errors = int(summary_match.group(3) or 0)
        duration = float(summary_match.group(4) or 0)

    for line in output.splitlines():
        if line.startswith("PASSED") or line.startswith("FAILED"):
            parts = line.split(" ", 1)
            ok = parts[0] == "PASSED"
            tid = parts[1].strip() if len(parts) > 1 else line
            test_results.append(TestResult(test_id=tid, passed=ok, duration_ms=0.0))

    return test_results, passed, failed, errors, duration


def _parse_coverage_json(cov_json_path: str, threshold: float) -> CoverageReport:
    try:
        with open(cov_json_path) as f:  # noqa: PTH123
            data = json.load(f)
        files = data.get("files", {})
        total_cov = data.get("totals", {}).get("percent_covered", 0.0)
        per_file = {p: v.get("summary", {}).get("percent_covered", 0.0) for p, v in files.items()}
        uncovered = {p: v.get("missing_lines", []) for p, v in files.items()}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        total_cov, per_file, uncovered = 0.0, {}, {}
    return CoverageReport(
        total_coverage=total_cov,
        per_file=per_file,
        uncovered_lines=uncovered,
        meets_threshold=total_cov >= threshold,
    )
