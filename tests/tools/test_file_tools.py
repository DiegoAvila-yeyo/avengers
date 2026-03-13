"""tests/tools/test_file_tools.py — Suite AMD-01 ROOT JAIL para file_tools.

Valida que:
- resolve_safe_path bloquea cualquier intento de path traversal.
- write_file crea directorios padre automáticamente.
- read_file devuelve el contenido correcto.
- Las excepciones lanzadas son RootJailViolationError.
"""

from __future__ import annotations

import pytest

from core.exceptions import RootJailViolationError
from tools.file_tools import PROJECT_ROOT, read_file, resolve_safe_path, write_file


# ── resolve_safe_path: rutas válidas ─────────────────────────────────────────


def test_valid_path_resolves_inside_root() -> None:
    result = resolve_safe_path("output/artifact.py")
    assert result.is_relative_to(PROJECT_ROOT)
    assert result == PROJECT_ROOT / "output" / "artifact.py"


def test_project_root_dot_resolves_correctly() -> None:
    assert resolve_safe_path(".") == PROJECT_ROOT


# ── resolve_safe_path: path traversal → RootJailViolationError ───────────────


@pytest.mark.parametrize(
    "evil_path",
    [
        "../../etc/passwd",
        "../../../tmp/evil",
        "/etc/passwd",
        "/tmp/bad",
        "output/../../etc/passwd",
        "blueprints/../../../etc/hosts",
    ],
)
def test_path_traversal_raises_root_jail_violation(evil_path: str) -> None:
    with pytest.raises(RootJailViolationError):
        resolve_safe_path(evil_path)


# ── write_file: crea directorios padre automáticamente ───────────────────────


def test_write_file_creates_parent_directories(tmp_path: pytest.FixtureLookupError, monkeypatch: pytest.MonkeyPatch) -> None:
    """write_file debe crear carpetas intermedias si no existen."""
    import tools.file_tools as ft

    original_root = ft.PROJECT_ROOT
    monkeypatch.setattr(ft, "PROJECT_ROOT", tmp_path)

    nested = "deep/nested/dir/hello.txt"
    result = write_file(nested, "hola mundo")

    assert result.exists()
    assert result.read_text() == "hola mundo"
    assert result.parent.is_dir()

    monkeypatch.setattr(ft, "PROJECT_ROOT", original_root)


def test_write_file_returns_absolute_path(tmp_path: pytest.FixtureLookupError, monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.file_tools as ft

    monkeypatch.setattr(ft, "PROJECT_ROOT", tmp_path)
    result = write_file("out/file.txt", "contenido")
    assert result.is_absolute()


# ── read_file ─────────────────────────────────────────────────────────────────


def test_read_file_returns_content(tmp_path: pytest.FixtureLookupError, monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.file_tools as ft

    monkeypatch.setattr(ft, "PROJECT_ROOT", tmp_path)
    (tmp_path / "data.txt").write_text("avengers assemble")
    assert read_file("data.txt") == "avengers assemble"


def test_read_file_nonexistent_raises_file_not_found(tmp_path: pytest.FixtureLookupError, monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.file_tools as ft

    monkeypatch.setattr(ft, "PROJECT_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        read_file("nope.txt")
