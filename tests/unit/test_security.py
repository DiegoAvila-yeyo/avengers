"""tests/unit/test_security.py — AMD-01 ROOT JAIL: validación de resolve_safe_path.

Verifica que ninguna ruta puede escapar de PROJECT_ROOT.
Protocolo Widow: ningún archivo temporal queda tras los tests.
"""

from __future__ import annotations

import pytest

from tools.file_tools import PROJECT_ROOT, PathEscapeError, resolve_safe_path


# ── Caso 1: Rutas válidas dentro del proyecto ─────────────────────────────────


def test_valid_relative_path_resolves_correctly() -> None:
    """Una ruta relativa válida debe resolverse dentro de PROJECT_ROOT."""
    result = resolve_safe_path("output/artifact.py")
    assert result == PROJECT_ROOT / "output" / "artifact.py"
    assert result.is_relative_to(PROJECT_ROOT)


def test_valid_nested_path_resolves_correctly() -> None:
    """Una ruta con subdirectorios válida debe resolverse correctamente."""
    result = resolve_safe_path("missions/mission-001.yaml")
    assert result.is_relative_to(PROJECT_ROOT)
    assert result == PROJECT_ROOT / "missions" / "mission-001.yaml"


def test_valid_tools_path_resolves_correctly() -> None:
    """Ruta a un archivo existente dentro de tools/ debe resolverse sin error."""
    result = resolve_safe_path("tools/file_tools.py")
    assert result.is_relative_to(PROJECT_ROOT)
    assert result.name == "file_tools.py"


def test_project_root_itself_is_valid() -> None:
    """La raíz del proyecto con '.' debe resolverse a PROJECT_ROOT."""
    result = resolve_safe_path(".")
    assert result == PROJECT_ROOT


# ── Caso 2: Path Traversal → debe lanzar PathEscapeError ─────────────────────


def test_parent_traversal_raises_path_escape_error() -> None:
    """../../etc/passwd debe lanzar PathEscapeError (AMD-01 ROOT JAIL)."""
    with pytest.raises(PathEscapeError):
        resolve_safe_path("../../etc/passwd")


def test_deep_traversal_raises_path_escape_error() -> None:
    """Múltiples saltos de directorio deben ser rechazados."""
    with pytest.raises(PathEscapeError):
        resolve_safe_path("../../../tmp/evil_file")


def test_absolute_path_outside_project_raises_error() -> None:
    """/tmp/bad es una ruta absoluta fuera del proyecto — debe fallar."""
    with pytest.raises(PathEscapeError):
        resolve_safe_path("/tmp/bad")


def test_absolute_system_path_raises_error() -> None:
    """/etc/passwd debe lanzar PathEscapeError."""
    with pytest.raises(PathEscapeError):
        resolve_safe_path("/etc/passwd")


def test_traversal_hidden_in_subdir_raises_error() -> None:
    """output/../../etc/passwd debe ser detectado y rechazado."""
    with pytest.raises(PathEscapeError):
        resolve_safe_path("output/../../etc/passwd")


def test_traversal_via_symlink_notation_raises_error() -> None:
    """Variante con doble punto al inicio de segmento debe ser rechazada."""
    with pytest.raises(PathEscapeError):
        resolve_safe_path("blueprints/../../../etc/hosts")
