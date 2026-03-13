"""tools/map_tools.py — Helpers para actualizar MAP.yaml durante Fase 3.

Extrae la lógica de lectura/escritura del MAP para cumplir el límite de
200 líneas del Protocolo Hulk en iron_coder.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

import yaml

from core.blueprint_schema import FileEntry, MissionMap
from tools.file_tools import read_file, write_file


def load_mission_map(map_path: str) -> MissionMap:
    """Lee y deserializa MAP.yaml en un MissionMap.

    Args:
        map_path: Ruta relativa al MAP.yaml (desde PROJECT_ROOT).

    Returns:
        MissionMap instanciado.

    Raises:
        RootJailViolationError: Si map_path escapa del proyecto.
        FileNotFoundError: Si el archivo no existe.
    """
    raw = read_file(map_path)
    data = yaml.safe_load(raw)
    return MissionMap.model_validate(data)


def save_mission_map(map_path: str, mission_map: MissionMap) -> None:
    """Serializa y escribe el MissionMap actualizado en MAP.yaml.

    Args:
        map_path:    Ruta relativa al MAP.yaml.
        mission_map: Instancia actualizada.
    """
    mission_map.updated_at = datetime.now(timezone.utc)  # noqa: UP017
    write_file(map_path, yaml.dump(mission_map.model_dump(mode="json"), allow_unicode=True))


def update_file_entry(
    map_path: str,
    file_path: str,
    *,
    status: str = "created",
    line_count: int | None = None,
) -> None:
    """Actualiza el FileEntry correspondiente en MAP.yaml.

    Si no existe una entrada para file_path, la operación es silenciosa.

    Args:
        map_path:   Ruta relativa al MAP.yaml.
        file_path:  Valor de FileEntry.path a buscar.
        status:     Nuevo status (default "created").
        line_count: Número de líneas del archivo generado.
    """
    mission_map = load_mission_map(map_path)
    for entry in mission_map.files:
        if entry.path == file_path:
            entry.status = status
            if line_count is not None:
                entry.line_count = line_count
            break
    save_mission_map(map_path, mission_map)


def add_file_entry(map_path: str, entry: FileEntry) -> None:
    """Añade un nuevo FileEntry al MAP.yaml (para conectores Fabricator).

    Args:
        map_path: Ruta relativa al MAP.yaml.
        entry:    FileEntry a añadir.
    """
    mission_map = load_mission_map(map_path)
    mission_map.files.append(entry)
    save_mission_map(map_path, mission_map)
