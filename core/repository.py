"""core/repository.py — Repositorio de Misiones (AMD-05 PERSISTENCIA).

Encapsula todas las operaciones de BD sobre el modelo Mission.
Colección MongoDB: "missions" — _id = mission_id.

Métodos AMD-05:
    save_mission(mission)                  → inserta misión nueva.
    get_mission(mission_id)                → recupera por ID.
    update_status(mission_id, status, ...) → actualiza status y fase.

Extra:
    append_log(mission_id, entry)          → push con TTL de 50 entradas.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorCollection

from core.database import db_manager
from core.models import Mission, MissionStatus

logger = logging.getLogger(__name__)

_COLLECTION = "missions"


# ── Serialización ─────────────────────────────────────────────────────────────


def _to_doc(mission: Mission) -> dict:  # type: ignore[type-arg]
    """Convierte Mission a dict para MongoDB (_id ← mission_id)."""
    doc = mission.model_dump(mode="json")
    doc["_id"] = doc.pop("mission_id")
    return doc


def _from_doc(doc: dict) -> Mission:  # type: ignore[type-arg]
    """Convierte un documento MongoDB a Mission (mission_id ← _id)."""
    raw = dict(doc)
    raw["mission_id"] = str(raw.pop("_id"))
    return Mission.model_validate(raw)


# ── Repositorio ───────────────────────────────────────────────────────────────


class MissionRepository:
    """Repositorio async para el modelo Mission.

    Requiere que `db_manager.connect()` haya sido llamado antes del primer uso.
    """

    @property
    def _col(self) -> AsyncIOMotorCollection:  # type: ignore[type-arg]
        return db_manager.get_database()[_COLLECTION]

    # ── AMD-05: Métodos obligatorios ──────────────────────────────────────────

    async def save_mission(self, mission: Mission) -> str:
        """Persiste una misión nueva en MongoDB.

        Returns:
            mission_id de la misión insertada.
        Raises:
            pymongo.errors.DuplicateKeyError si ya existe ese mission_id.
        """
        doc = _to_doc(mission)
        await self._col.insert_one(doc)
        logger.info("Misión guardada: %s", mission.mission_id)
        return mission.mission_id

    async def get_mission(self, mission_id: str) -> Mission | None:
        """Recupera una misión por su ID.

        Returns:
            Mission si existe, None si no se encontró.
        """
        doc = await self._col.find_one({"_id": mission_id})
        if doc is None:
            logger.debug("Misión no encontrada: %s", mission_id)
            return None
        return _from_doc(doc)

    async def update_status(
        self,
        mission_id: str,
        status: MissionStatus,
        current_phase: int | None = None,
    ) -> bool:
        """Actualiza el status de una misión y, opcionalmente, la fase actual.

        Returns:
            True si se actualizó el documento, False si no existía.
        """
        fields: dict[str, object] = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if current_phase is not None:
            fields["current_phase"] = current_phase

        result = await self._col.update_one(
            {"_id": mission_id},
            {"$set": fields},
        )
        updated = result.matched_count > 0
        if updated:
            logger.info("Misión %s → status=%s", mission_id, status.value)
        else:
            logger.warning("update_status: misión no encontrada: %s", mission_id)
        return updated

    # ── Métodos auxiliares ────────────────────────────────────────────────────

    async def append_log(self, mission_id: str, entry: dict) -> bool:  # type: ignore[type-arg]
        """Añade una LogEntry al historial de la misión.

        Aplica TTL de 50 entradas (slice negativo) según ARCHITECTURE.md § 5.

        Returns:
            True si el documento existía y fue actualizado.
        """
        result = await self._col.update_one(
            {"_id": mission_id},
            {
                "$push": {
                    "log": {
                        "$each": [entry],
                        "$slice": -50,
                    }
                },
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            },
        )
        return result.matched_count > 0


# Singleton — reutilizar entre módulos.
mission_repo = MissionRepository()
