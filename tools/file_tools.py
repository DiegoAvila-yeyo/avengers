"""tools/file_tools.py — AMD-01 ROOT JAIL.

Toda operación de I/O de archivos debe pasar por resolve_safe_path()
para garantizar que ningún archivo se crea fuera de PROJECT_ROOT.
"""

from __future__ import annotations

from pathlib import Path

# Raíz inmutable del proyecto — nunca se sobreescribe en runtime.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]


class PathEscapeError(ValueError):
    """Se lanza cuando una ruta intenta salir de PROJECT_ROOT."""


def resolve_safe_path(relative: str | Path) -> Path:
    """Resuelve *relative* contra PROJECT_ROOT y valida que no escape.

    Args:
        relative: Ruta relativa al proyecto (str o Path).

    Returns:
        Ruta absoluta resuelta dentro de PROJECT_ROOT.

    Raises:
        PathEscapeError: Si la ruta resuelta queda fuera de PROJECT_ROOT.

    Example:
        >>> resolve_safe_path("output/my_file.py")
        PosixPath('/…/avengers/output/my_file.py')
        >>> resolve_safe_path("../../etc/passwd")  # ← lanza PathEscapeError
    """
    resolved = (PROJECT_ROOT / relative).resolve()
    if not resolved.is_relative_to(PROJECT_ROOT):
        raise PathEscapeError(
            f"AMD-01 ROOT JAIL — ruta fuera del proyecto: {resolved!r}"
        )
    return resolved


def safe_write_text(relative: str | Path, content: str, encoding: str = "utf-8") -> Path:
    """Escribe *content* en *relative* (relativo a PROJECT_ROOT) de forma segura.

    Crea los directorios padre si no existen.

    Returns:
        Ruta absoluta del archivo escrito.

    Raises:
        PathEscapeError: Si la ruta intenta salir de PROJECT_ROOT.
    """
    target = resolve_safe_path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=encoding)
    return target


def safe_read_text(relative: str | Path, encoding: str = "utf-8") -> str:
    """Lee y devuelve el contenido de *relative* (relativo a PROJECT_ROOT).

    Raises:
        PathEscapeError: Si la ruta intenta salir de PROJECT_ROOT.
        FileNotFoundError: Si el archivo no existe.
    """
    source = resolve_safe_path(relative)
    return source.read_text(encoding=encoding)
