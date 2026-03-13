"""core/checkpoints.py — Motor de checkpoints: pausar, notificar, reanudar.

Un Checkpoint = punto donde el humano tiene control total sobre la misión.
Persistencia Estricta: AWAITING_HUMAN se graba en DB ANTES de notificar.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from pydantic import BaseModel, Field

from core.models import AgentRole, Mission, MissionStatus, RetryPolicy
from core.repository import MissionRepository

logger = logging.getLogger(__name__)

VALID_RESOLUTIONS = frozenset({"resume", "abort", "retry_override"})


class CheckpointRecord(BaseModel):
    """Registro de un checkpoint bloqueante."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str
    triggered_by: str  # "retry_exhausted" | "phase_gate" | "manual"
    blocking_agent: AgentRole
    reason: str
    retry_attempts: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    resolution: str | None = None  # "resume" | "abort" | "retry_override"


class CheckpointNotifier(Protocol):
    """Interfaz de notificación desacoplada del canal de entrega."""

    async def notify(self, checkpoint: CheckpointRecord) -> None: ...


class ConsoleCheckpointNotifier:
    """Implementación dev: imprime el checkpoint en consola."""

    async def notify(self, checkpoint: CheckpointRecord) -> None:
        print(  # noqa: T201
            f"\n⚠️  CHECKPOINT [{checkpoint.checkpoint_id}] — Misión {checkpoint.mission_id}\n"
            f"  Razón: {checkpoint.reason}\n"
            f"  Agente bloqueado: {checkpoint.blocking_agent.value}\n"
            f"  Acción requerida: resolve con 'resume', 'abort' o 'retry_override'\n"
        )


class CheckpointManager:
    """Gestiona los Checkpoints bloqueantes del sistema AVENGERS.

    Persistencia Estricta: el estado en DB es la fuente de verdad.
    Los checkpoints se guardan en la colección MongoDB 'checkpoints'.
    """

    def __init__(
        self,
        repo: MissionRepository,
        notifier: CheckpointNotifier,
        checkpoint_col: Any,
    ) -> None:
        self._repo = repo
        self._notifier = notifier
        self._col = checkpoint_col

    async def trigger(
        self,
        mission: Mission,
        reason: str,
        triggered_by: str,
        blocking_agent: AgentRole,
        retry_attempts: int = 0,
    ) -> CheckpointRecord:
        """Crea checkpoint, persiste en DB, cambia status → AWAITING_HUMAN, notifica."""
        record = CheckpointRecord(
            mission_id=mission.mission_id,
            triggered_by=triggered_by,
            blocking_agent=blocking_agent,
            reason=reason,
            retry_attempts=retry_attempts,
        )

        # 1. Persiste checkpoint en colección separada
        doc = record.model_dump(mode="json")
        doc["_id"] = doc.pop("checkpoint_id")
        await self._col.insert_one(doc)

        # 2. Persiste misión con status AWAITING_HUMAN (fuente de verdad)
        mission.status = MissionStatus.AWAITING_HUMAN
        mission.updated_at = datetime.now(timezone.utc)
        await self._repo.save_mission(mission)

        # 3. Notifica — puede fallar sin comprometer la persistencia
        try:
            await self._notifier.notify(record)
        except Exception:
            logger.warning("Notificación falló — estado en DB es fuente de verdad.")

        return record

    async def resolve(
        self,
        checkpoint_id: str,
        resolution: str,
        mission: Mission,
    ) -> Mission:
        """Resuelve un checkpoint y transiciona el estado de la misión."""
        if resolution not in VALID_RESOLUTIONS:
            raise ValueError(f"Resolución inválida: {resolution!r}")

        resolved_at = datetime.now(timezone.utc)

        if resolution == "abort":
            mission.status = MissionStatus.ABORTED
        else:  # "resume" o "retry_override"
            if resolution == "retry_override":
                mission.retry_policy = RetryPolicy()
            mission.status = MissionStatus.IN_PROGRESS

        mission.updated_at = resolved_at
        await self._repo.save_mission(mission)
        await self._col.update_one(
            {"_id": checkpoint_id},
            {"$set": {"resolution": resolution, "resolved_at": resolved_at.isoformat()}},
        )
        return mission

    async def get_pending(self, mission_id: str) -> list[CheckpointRecord]:
        """Retorna checkpoints sin resolver para una misión."""
        cursor = self._col.find({"mission_id": mission_id, "resolution": None})
        docs = await cursor.to_list(length=100)
        return [
            CheckpointRecord(**{**doc, "checkpoint_id": str(doc.pop("_id"))})
            for doc in docs
        ]
