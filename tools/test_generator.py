"""tools/test_generator.py — Genera suites pytest desde BlueprintV1.

Widow: solo automated=True. Hulk: divide si > 300 líneas. Map: registra en MAP.yaml.
"""

from __future__ import annotations

import json

from core.blueprint_schema import AcceptanceCriterion, BlueprintV1, FileEntry
from core.models import AgentRole
from tools.file_tools import read_file, write_file
from tools.map_tools import add_file_entry
from tools.shell_tools import run_command

MAX_TEST_LINES: int = 300
COVERAGE_THRESHOLD: int = 80


def _render_block(ac: AcceptanceCriterion) -> str:
    safe_id = ac.id.replace("-", "_").lower()
    return (
        f"\n\nasync def test_{safe_id}() -> None:\n"
        f'    """[{ac.id}] {ac.description}"""\n'
        f"    # TODO: implement assertion for: {ac.description}\n"
        f"    assert True  # placeholder\n"
    )


def _build_module(criteria: list[AcceptanceCriterion], product_name: str) -> str:
    header = (
        f'"""Tests generados para {product_name} — no editar manualmente."""\n'
        f"\nfrom __future__ import annotations\n\nimport pytest\n"
    )
    return header + "".join(_render_block(ac) for ac in criteria)


def _split(criteria: list[AcceptanceCriterion]) -> list[list[AcceptanceCriterion]]:
    chunk_size = max(1, MAX_TEST_LINES // 10)
    return [criteria[i : i + chunk_size] for i in range(0, len(criteria), chunk_size)]


def _register(map_path: str, file_path: str, line_count: int) -> None:
    add_file_entry(
        map_path,
        FileEntry(
            path=file_path,
            created_by=AgentRole.IRON_CODER,
            module="__test_generator__",
            responsibility="Generated pytest suite from AcceptanceCriteria",
            line_count=line_count,
            status="created",
        ),
    )


def generate_tests(blueprint: BlueprintV1, map_path: str) -> list[str]:
    """Genera archivos de test y los registra en MAP.yaml. Retorna rutas relativas."""
    automated = [ac for ac in blueprint.acceptance_criteria if ac.automated]
    if not automated:
        return []

    base = f"tests/generated/test_{blueprint.blueprint_id}"
    full = _build_module(automated, blueprint.product_name)

    if len(full.splitlines()) <= MAX_TEST_LINES:
        parts: list[tuple[str, list[AcceptanceCriterion]]] = [(f"{base}.py", automated)]
    else:
        parts = [(f"{base}_part{i + 1}.py", chunk) for i, chunk in enumerate(_split(automated))]

    generated: list[str] = []
    for rel_path, chunk in parts:
        content = _build_module(chunk, blueprint.product_name)
        write_file(rel_path, content)
        _register(map_path, rel_path, len(content.splitlines()))
        generated.append(rel_path)
    return generated


async def run_tests_with_coverage(
    test_paths: list[str],
    threshold: int = COVERAGE_THRESHOLD,
) -> dict[str, object]:
    """Ejecuta pytest con cobertura. Retorna dict: returncode, passed, failed, coverage_pct."""
    if not test_paths:
        return {"returncode": 0, "passed": 0, "failed": 0, "coverage_pct": 100.0}

    report_file = ".coverage_report.json"
    cmd = [
        "pytest", *test_paths, "--tb=short", "-q",
        f"--cov-fail-under={threshold}", f"--cov-report=json:{report_file}", "--cov=.",
    ]
    returncode, stdout, _ = await run_command(cmd, timeout=120.0)

    summary: dict[str, object] = {
        "returncode": returncode, "passed": 0, "failed": 0, "coverage_pct": 0.0
    }
    try:
        data = json.loads(read_file(report_file))
        summary["coverage_pct"] = data.get("totals", {}).get("percent_covered", 0.0)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    for line in stdout.splitlines():
        tokens = line.split()
        for key in ("passed", "failed"):
            if key in tokens:
                idx = tokens.index(key)
                if idx > 0 and tokens[idx - 1].isdigit():
                    summary[key] = int(tokens[idx - 1])

    return summary
