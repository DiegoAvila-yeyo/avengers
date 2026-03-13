"""tests/tools/test_hallucination_detector.py — Tests para HallucinationDetector."""

from __future__ import annotations

from core.blueprint_schema import ApiEndpoint, BlueprintV1, DataModel, ModuleSpec
from tools.hallucination_detector import HallucinationDetector

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_blueprint(
    endpoints: list[ApiEndpoint] | None = None,
    models: list[DataModel] | None = None,
) -> BlueprintV1:
    return BlueprintV1(
        blueprint_id="bp-test",
        mission_id="m-test",
        product_name="Test",
        problem_statement="Test",
        target_audience="devs",
        tech_stack=["fastapi"],
        modules=[ModuleSpec(module_name="core", responsibility="core logic", estimated_lines=50)],
        data_models=models or [],
        api_endpoints=endpoints or [],
        acceptance_criteria=[],
    )


def _make_detector(
    endpoints: list[ApiEndpoint] | None = None,
    models: list[DataModel] | None = None,
    allowed: set[str] | None = None,
) -> HallucinationDetector:
    bp = _make_blueprint(endpoints=endpoints, models=models)
    packages = allowed if allowed is not None else {"fastapi", "httpx", "pydantic"}
    return HallucinationDetector(blueprint=bp, allowed_packages=packages)


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_detects_unknown_import() -> None:
    """Detecta import de librería no declarada en pyproject.toml."""
    detector = _make_detector(allowed={"fastapi"})
    code = "import pandas\n"
    violations = detector.check_imports(code, "agents/some_agent.py")
    assert len(violations) == 1
    assert "pandas" in violations[0].detail
    assert violations[0].severity == "error"


def test_allows_stdlib_imports() -> None:
    """Permite imports de módulos de la stdlib (os, sys, pathlib…)."""
    detector = _make_detector(allowed=set())
    code = "import os\nimport sys\nfrom pathlib import Path\n"
    violations = detector.check_imports(code, "agents/some_agent.py")
    assert violations == []


def test_detects_undeclared_endpoint() -> None:
    """Detecta endpoint hardcodeado que no existe en el Blueprint."""
    declared = ApiEndpoint(
        method="GET",
        path="/users",
        description="list users",
        response_schema={"type": "array"},
    )
    detector = _make_detector(endpoints=[declared])
    code = 'response = client.get("/hidden/route")\n'
    violations = detector.check_endpoints(code, "agents/iron_coder.py")
    assert any("/hidden/route" in v.detail for v in violations)
    assert all(v.severity == "warning" for v in violations)


def test_detects_direct_env_access() -> None:
    """Detecta uso directo de os.environ / os.getenv fuera de settings."""
    detector = _make_detector()
    code = 'api_key = os.environ["API_KEY"]\n'
    violations = detector.check_env_access(code, "agents/thor.py")
    assert len(violations) == 1
    assert violations[0].severity == "error"


def test_allows_env_access_in_settings_file() -> None:
    """Permite acceso a entorno dentro de core/settings.py."""
    detector = _make_detector()
    code = 'DB_URL = os.environ.get("DATABASE_URL", "sqlite://")\n'
    violations = detector.check_env_access(code, "core/settings.py")
    assert violations == []


def test_detects_undeclared_data_model() -> None:
    """Detecta clase no declarada en Blueprint data_models."""
    model = DataModel(name="User", fields={"id": "str", "name": "str"})
    detector = _make_detector(models=[model])
    code = "class GhostModel:\n    pass\n"
    violations = detector.check_data_models(code, "agents/iron_coder.py")
    assert any("GhostModel" in v.detail for v in violations)
    assert all(v.severity == "warning" for v in violations)
