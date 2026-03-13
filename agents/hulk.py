"""agents/hulk.py — Guardrail del sistema (Fase 4).

Escanea archivos generados por Iron-Coder/Vision-UI en busca de violaciones:
líneas > 300, imports no usados (ruff F401) y patrones prohibidos (open, subprocess…).
Solo reporta — NUNCA modifica código (modificación = Black Widow).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import BaseModel

from core.exceptions import HulkViolationError
from core.models import AgentRole, LogEntry, Mission
from tools.file_tools import read_file, resolve_safe_path, write_file
from tools.shell_tools import run_command

logger = logging.getLogger(__name__)

MAX_FILE_LINES: int = 300


# ── Modelos de dominio ────────────────────────────────────────────────────────


class ViolationType(str, Enum):  # noqa: UP042
    LINE_LIMIT = "line_limit"
    UNUSED_IMPORT = "unused_import"
    DEAD_CODE = "dead_code"
    FORBIDDEN_PATTERN = "forbidden"


class GuardrailViolation(BaseModel):
    file_path: str
    violation_type: ViolationType
    line_number: int | None = None
    detail: str
    severity: str  # "error" | "warning"


class GuardrailReport(BaseModel):
    mission_id: str
    scanned_files: int
    violations: list[GuardrailViolation]
    passed: bool
    generated_at: datetime


# ── Agente ────────────────────────────────────────────────────────────────────


class HulkAgent:
    """Guardrail del sistema. Bloquea si encuentra violaciones 'error'."""

    FORBIDDEN_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"\bopen\s*\(", "open() directo — usa file_tools.read_file()/write_file()"),
        (r"\bos\.system\s*\(", "os.system() directo — usa shell_tools.run_command()"),
        (r"\bsubprocess\.", "subprocess directo — usa shell_tools.run_command()"),
        (r"\brequests\.", "requests síncrono — usa httpx async"),
    ]

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    async def run(self, mission: Mission) -> Mission:
        """Escanea archivos con status='created' en MAP.yaml y genera hulk_report.yaml."""
        map_path = f"missions/{mission.mission_id}/MAP.yaml"
        try:
            raw = read_file(map_path)
            mission_map: dict = yaml.safe_load(raw)
        except FileNotFoundError:
            mission_map = {"files": []}

        files_to_scan = [
            f["path"]
            for f in mission_map.get("files", [])
            if f.get("status") == "created" and f.get("path", "").endswith(".py")
        ]

        all_violations: list[GuardrailViolation] = []
        for fp in files_to_scan:
            all_violations.extend(await self.scan_file(fp))

        error_count = sum(1 for v in all_violations if v.severity == "error")
        report = GuardrailReport(
            mission_id=mission.mission_id,
            scanned_files=len(files_to_scan),
            violations=all_violations,
            passed=error_count == 0,
            generated_at=datetime.now(timezone.utc),  # noqa: UP017
        )

        report_path = f"missions/{mission.mission_id}/hulk_report.yaml"
        write_file(report_path, yaml.dump(report.model_dump(mode="json"), allow_unicode=True))

        mission.log.append(
            LogEntry(
                agent=AgentRole.HULK,
                event="guardrail_scan_complete",
                artifact=report_path,
            )
        )

        if not report.passed:
            raise HulkViolationError(mission.mission_id, error_count)

        return mission

    async def scan_file(self, file_path: str) -> list[GuardrailViolation]:
        """Ejecuta todos los checks sobre un archivo .py."""
        violations: list[GuardrailViolation] = []

        limit_v = await self._check_line_limit(file_path)
        if limit_v:
            violations.append(limit_v)

        violations.extend(await self._check_imports(file_path))
        violations.extend(await self._check_forbidden(file_path))

        return violations

    async def _check_line_limit(self, file_path: str) -> GuardrailViolation | None:
        """Verifica que el archivo no supere MAX_FILE_LINES."""
        try:
            content = read_file(file_path)
        except FileNotFoundError:
            return None
        line_count = len(content.splitlines())
        if line_count > MAX_FILE_LINES:
            return GuardrailViolation(
                file_path=file_path,
                violation_type=ViolationType.LINE_LIMIT,
                line_number=line_count,
                detail=(
                    f"Archivo tiene {line_count} líneas "
                    f"(máx. {MAX_FILE_LINES}) — Protocolo Hulk."
                ),
                severity="error",
            )
        return None

    async def _check_imports(self, file_path: str) -> list[GuardrailViolation]:
        """Detecta imports no usados via ruff F401."""
        try:
            abs_path = str(resolve_safe_path(file_path))
        except Exception:
            return []
        _, stdout, _ = await run_command(
            ["ruff", "check", abs_path, "--select", "F401", "--output-format", "json"]
        )
        if not stdout.strip():
            return []
        try:
            items: list[dict] = json.loads(stdout)
        except json.JSONDecodeError:
            return []
        return [
            GuardrailViolation(
                file_path=file_path,
                violation_type=ViolationType.UNUSED_IMPORT,
                line_number=item.get("location", {}).get("row"),
                detail=item.get("message", "Unused import"),
                severity="warning",
            )
            for item in items
        ]

    async def _check_forbidden(self, file_path: str) -> list[GuardrailViolation]:
        """Detecta patrones prohibidos usando regex sobre el contenido del archivo."""
        try:
            content = read_file(file_path)
        except FileNotFoundError:
            return []
        violations: list[GuardrailViolation] = []
        for line_no, line in enumerate(content.splitlines(), start=1):
            for pattern, detail in self.FORBIDDEN_PATTERNS:
                if re.search(pattern, line):
                    violations.append(
                        GuardrailViolation(
                            file_path=file_path,
                            violation_type=ViolationType.FORBIDDEN_PATTERN,
                            line_number=line_no,
                            detail=detail,
                            severity="error",
                        )
                    )
        return violations
