"""core/state_log.py — Gestor del State Log de misiones (Protocolo JIT).

Cada append() persiste en MongoDB de forma async. Si la persistencia falla,
se lanza StatePersistenceError — nunca se pierde un evento sin respaldo en BD.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.models import LogEntry, Mission

logger = logging.getLogger(__name__)

_MAX_LOG_ENTRIES = 50


class StateLogManager:
    """Gestiona el historial de eventos de una misión con TTL de 50 entradas.

    Principio JIT: solo se inyecta el State Log (últimas 50 entradas) a cada agente.
    """

    def __init__(self, repo: object) -> None:
        self._repo = repo

    async def append(
        self,
        mission: Mission,
        agent: str,
        event: str,
        artifact: str | None = None,
    ) -> Mission:
        """Añade un LogEntry al State Log y persiste de forma async.

        Raises:
            StatePersistenceError: si no se puede sincronizar con MongoDB.
        """
        from core.exceptions import StatePersistenceError  # local import to avoid circular

        entry = LogEntry(
            ts=datetime.now(timezone.utc),
            agent=agent,
            event=event,
            artifact=artifact,
        )
        mission.log.append(entry)
        if len(mission.log) > _MAX_LOG_ENTRIES:
            mission.log = mission.log[-_MAX_LOG_ENTRIES:]

        try:
            await self._repo.save_mission(mission)  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("StatePersistenceError al persistir log: %s", exc)
            raise StatePersistenceError(str(exc)) from exc

        logger.debug("Log append [%s] %s → %s", agent, event, artifact)
        return mission

    def get_context_window(self, mission: Mission) -> list[LogEntry]:
        """Retorna las últimas _MAX_LOG_ENTRIES entradas del State Log."""
        return mission.log[-_MAX_LOG_ENTRIES:]
