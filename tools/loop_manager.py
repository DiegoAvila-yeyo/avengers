"""tools/loop_manager.py — Gestor del cierre de misión y apertura del nuevo ciclo (Prompt #24)."""

from __future__ import annotations

import contextlib
import logging
import shutil
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel

from core.models import AgentRole, LogEntry, Mission, MissionStatus
from tools.file_tools import read_file, resolve_safe_path, write_file

if TYPE_CHECKING:
    from agents.nick_fury import NickFuryOrchestrator
    from core.checkpoints import CheckpointManager
    from core.repository import MissionRepository
    from tools.feedback_collector import FeedbackSummary

logger = logging.getLogger(__name__)
_DEFAULT_TOKEN_BUDGET = 100_000


class MissionSummary(BaseModel):
    """Resumen ejecutivo de una misión completada para el archivo histórico."""

    mission_id: str
    product_name: str
    status: MissionStatus
    total_tokens_used: int
    total_duration_seconds: float
    artifacts_created: int
    tests_passing: int
    coverage_pct: float
    deploy_url: str | None
    feedback_summary_ref: str | None
    closed_at: datetime


class LoopManager:
    """Gestiona el cierre ordenado de una misión y el arranque de la siguiente.

    Nick Fury delega aquí la lógica del Bucle Infinito.
    """

    def __init__(
        self,
        orchestrator: NickFuryOrchestrator,
        checkpoint_manager: CheckpointManager,
        repo: MissionRepository,
    ) -> None:
        self._orchestrator = orchestrator
        self._checkpoint = checkpoint_manager
        self._repo = repo

    async def close_mission(self, mission: Mission) -> MissionSummary:
        """Cierre ordenado de una misión completada."""
        mission.status = MissionStatus.DONE
        mission.updated_at = datetime.now(timezone.utc)  # noqa: UP017
        now = mission.updated_at
        duration = (now - mission.created_at).total_seconds()

        artifacts = 0
        map_path = f"missions/{mission.mission_id}/MAP.yaml"
        try:
            data = yaml.safe_load(read_file(map_path))
            artifacts = sum(1 for f in (data.get("files") or []) if f.get("status") == "created")
        except FileNotFoundError:
            pass

        feedback_ref: str | None = None
        feedback_path = f"missions/{mission.mission_id}/feedback_summary.yaml"
        try:
            read_file(feedback_path)
            feedback_ref = feedback_path
        except FileNotFoundError:
            pass

        summary = MissionSummary(
            mission_id=mission.mission_id,
            product_name=mission.mission_id,
            status=MissionStatus.DONE,
            total_tokens_used=0,
            total_duration_seconds=duration,
            artifacts_created=artifacts,
            tests_passing=0,
            coverage_pct=0.0,
            deploy_url=None,
            feedback_summary_ref=feedback_ref,
            closed_at=now,
        )
        write_file(
            f"missions/{mission.mission_id}/mission_summary.yaml",
            yaml.dump(summary.model_dump(mode="json"), allow_unicode=True),
        )
        with contextlib.suppress(FileNotFoundError):
            write_file(f"output/{mission.mission_id}/MAP_final.yaml", read_file(map_path))

        await self._repo.update_status(mission.mission_id, MissionStatus.DONE)

        cache_path = resolve_safe_path(f"output/scrape_cache/{mission.mission_id}")
        if cache_path.exists():
            shutil.rmtree(cache_path)

        logger.info("Misión %s cerrada → DONE", mission.mission_id)
        return summary

    def evaluate_next_cycle(
        self,
        summary: MissionSummary,
        feedback: FeedbackSummary,
    ) -> bool:
        """Decide si vale la pena lanzar un nuevo ciclo."""
        return (
            feedback.positive_ratio > 0.4
            and summary.coverage_pct >= 80.0
            and summary.total_tokens_used < _DEFAULT_TOKEN_BUDGET * 0.9
        )

    async def launch_next_cycle(
        self,
        prev_summary: MissionSummary,
        feedback: FeedbackSummary,
    ) -> Mission:
        """Inicia la siguiente iteración del Bucle Infinito."""
        await self._checkpoint.trigger(
            mission=Mission(mission_id=prev_summary.mission_id),
            reason=f"¿Autorizar nueva misión? Keyword sugerida: {feedback.suggested_keyword}",
            triggered_by="loop_closure",
            blocking_agent=AgentRole.NICK_FURY,
        )

        if not self.evaluate_next_cycle(prev_summary, feedback):
            logger.info("Bucle pausado — tracción insuficiente")
            raise RuntimeError("Bucle pausado — tracción insuficiente")

        new_mission = await self._orchestrator.create_mission()
        new_mission.log.append(LogEntry(
            agent=AgentRole.NICK_FURY.value,
            event="loop_feedback_keyword",
            artifact=feedback.suggested_keyword,
        ))
        new_mission.log.append(LogEntry(
            agent=AgentRole.NICK_FURY.value,
            event="thor_pain_signals",
            artifact="; ".join(feedback.pain_points),
        ))
        await self._repo.append_log(
            new_mission.mission_id,
            new_mission.log[-1].model_dump(mode="json"),
        )
        logger.info("Nueva misión lanzada: %s", new_mission.mission_id)
        return new_mission

    async def generate_factory_report(self) -> str:
        """Genera un reporte de rendimiento de la factoría completa."""
        done = await self._repo.list_by_status(MissionStatus.DONE)
        failed = await self._repo.list_by_status(MissionStatus.FAILED)

        avg_duration = 0.0
        if done:
            avg_duration = sum(
                (m.updated_at - m.created_at).total_seconds() for m in done
            ) / len(done)

        report = (
            "# AVENGERS — Factory Report\n\n"
            f"- Misiones completadas: {len(done)}\n"
            f"- Misiones fallidas: {len(failed)}\n"
            f"- Tiempo promedio (creación → cierre): {avg_duration:.1f}s\n"
            f"- Generado: {datetime.now(timezone.utc).isoformat()}\n"  # noqa: UP017
        )
        write_file("docs/factory_report.md", report)
        logger.info("Factory report generado: docs/factory_report.md")
        return report
