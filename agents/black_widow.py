"""agents/black_widow.py — The Cleaner (Fase 4).

Fragmenta archivos > 300L, elimina imports muertos y reemplaza patrones prohibidos.
Widow NUNCA modifica archivos de test.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel

from agents.hulk import GuardrailReport, GuardrailViolation, ViolationType
from core.models import AgentRole, LogEntry, Mission
from tools.file_tools import read_file, resolve_safe_path, write_file
from tools.shell_tools import run_command

if TYPE_CHECKING:
    from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ── Modelos ───────────────────────────────────────────────────────────────────


class RefactorAction(BaseModel):
    """Registro de una acción de refactorización aplicada."""

    file_path: str
    action_type: str  # "split" | "remove_dead_code" | "fix_imports" | "rename"
    description: str
    lines_before: int
    lines_after: int


class WidowReport(BaseModel):
    """Resumen del trabajo de Black Widow en una misión."""

    mission_id: str
    actions: list[RefactorAction]
    files_split: int
    dead_code_removed: int
    imports_fixed: int
    generated_at: datetime


# ── Agente ────────────────────────────────────────────────────────────────────


class BlackWidowAgent:
    """Black Widow: aplica correcciones del GuardrailReport de Hulk.

    No genera código nuevo — solo limpia y reorganiza. Nunca toca tests/.
    """

    def __init__(self, llm_client: LLMClient, project_root: Path) -> None:
        self._llm = llm_client
        self._root = project_root
    async def run(self, mission: Mission) -> Mission:
        """Lee hulk_report, procesa violaciones y genera widow_report."""
        report_path = f"missions/{mission.mission_id}/hulk_report.yaml"
        try:
            raw = read_file(report_path)
            report = GuardrailReport.model_validate(yaml.safe_load(raw))
        except FileNotFoundError:
            logger.info("No hulk_report encontrado para %s; nada que limpiar.", mission.mission_id)
            return mission

        actions: list[RefactorAction] = []
        new_files: list[str] = []
        seen: set[str] = set()

        for v in report.violations:
            if _is_test_file(v.file_path):
                continue
            key = f"{v.file_path}:{v.violation_type}"
            if key in seen:
                continue
            seen.add(key)

            if v.violation_type == ViolationType.LINE_LIMIT:
                created = await self._split_file(v.file_path, mission.mission_id)
                new_files.extend(created)
                if created:
                    actions.append(_action(
                        "split", v.file_path, f"Split into {len(created)} modules"
                    ))
            elif v.violation_type == ViolationType.UNUSED_IMPORT:
                count = await self._fix_imports(v.file_path)
                if count:
                    actions.append(_action("fix_imports", v.file_path, f"Fixed {count} imports"))
            elif v.violation_type == ViolationType.DEAD_CODE:
                count = await self._remove_dead_code(v.file_path)
                if count:
                    actions.append(_action(
                        "remove_dead_code", v.file_path, f"Removed ~{count} lines"
                    ))
            elif v.violation_type == ViolationType.FORBIDDEN_PATTERN:
                await self._replace_forbidden(v.file_path, v)
                actions.append(_action("rename", v.file_path, f"Replaced: {v.detail}"))

        if new_files:
            _update_map(mission.mission_id, new_files)

        widow_report = WidowReport(
            mission_id=mission.mission_id,
            actions=actions,
            files_split=sum(1 for a in actions if a.action_type == "split"),
            dead_code_removed=sum(1 for a in actions if a.action_type == "remove_dead_code"),
            imports_fixed=sum(1 for a in actions if a.action_type == "fix_imports"),
            generated_at=datetime.now(timezone.utc),  # noqa: UP017
        )
        out_path = f"missions/{mission.mission_id}/widow_report.yaml"
        write_file(out_path, yaml.dump(widow_report.model_dump(mode="json"), allow_unicode=True))

        mission.log.append(
            LogEntry(agent=AgentRole.BLACK_WIDOW, event="refactor_complete", artifact=out_path)
        )
        return mission

    async def _split_file(self, file_path: str, mission_id: str) -> list[str]:
        """Fragmenta un archivo > 300L en sub-módulos via LLM (tools/code_splitter)."""
        from tools.code_splitter import split_file_semantically

        try:
            content = read_file(file_path)
        except FileNotFoundError:
            return []
        return await split_file_semantically(file_path, content, self._llm, mission_id)

    async def _fix_imports(self, file_path: str) -> int:
        """Ejecuta ruff F401 --fix. Retorna número de imports corregidos."""
        try:
            abs_path = str(resolve_safe_path(file_path))
        except Exception:
            return 0
        rc, stdout, _ = await run_command(
            ["ruff", "check", abs_path, "--select", "F401", "--fix", "--output-format", "json"]
        )
        if rc != 0 or not stdout.strip():
            return 0
        try:
            return len(json.loads(stdout))
        except Exception:
            return 0

    async def _remove_dead_code(self, file_path: str) -> int:
        """Ejecuta ruff F811,F841 --fix. Retorna estimación de líneas eliminadas."""
        try:
            abs_path = str(resolve_safe_path(file_path))
        except Exception:
            return 0
        rc, stdout, _ = await run_command(
            ["ruff", "check", abs_path, "--select", "F811,F841", "--fix", "--output-format", "json"]
        )
        if rc != 0 or not stdout.strip():
            return 0
        try:
            return len(json.loads(stdout))
        except Exception:
            return 0

    async def _replace_forbidden(self, file_path: str, violation: GuardrailViolation) -> None:
        """Reemplaza patrones prohibidos via LLM."""
        from core.llm_client import AgentRole as LLMAgentRole
        from core.llm_client import LLMRequest

        try:
            content = read_file(file_path)
        except FileNotFoundError:
            return

        request = LLMRequest(
            role=LLMAgentRole.BLACK_WIDOW,
            system_prompt=(
                "Reemplaza el patrón prohibido con el equivalente seguro: "
                "file_tools.read_file()/write_file() en vez de open(), "
                "shell_tools.run_command() en vez de os.system()/subprocess. "
                "Devuelve SOLO código Python, sin markdown."
            ),
            user_message=f"Archivo: {file_path}\nViolación: {violation.detail}\n\n{content}",
            mission_id="widow-fix",
        )
        response = await self._llm.complete(request)
        write_file(file_path, response.content.strip())


def _is_test_file(file_path: str) -> bool:
    return file_path.startswith("tests/") or "/tests/" in file_path


def _action(action_type: str, file_path: str, description: str) -> RefactorAction:
    return RefactorAction(
        file_path=file_path,
        action_type=action_type,
        description=description,
        lines_before=0,
        lines_after=0,
    )


def _update_map(mission_id: str, new_files: list[str]) -> None:
    map_path = f"missions/{mission_id}/MAP.yaml"
    try:
        raw = read_file(map_path)
        mission_map: dict[str, object] = yaml.safe_load(raw) or {}
    except FileNotFoundError:
        mission_map = {}
    files: list[dict[str, object]] = mission_map.get("files", [])
    existing = {f.get("path") for f in files}
    for fp in new_files:
        if fp not in existing:
            files.append({"path": fp, "status": "created", "line_count": None})
    mission_map["files"] = files
    write_file(map_path, yaml.dump(mission_map, allow_unicode=True))
