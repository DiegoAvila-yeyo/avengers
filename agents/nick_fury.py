"""agents/nick_fury.py — Orquestador Central AVENGERS.

Nick Fury no ejecuta — coordina, persiste y protege la integridad del State Log.
Principio: Persistencia Estricta en cada mutación de estado.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from core.exceptions import (
    AgentExecutionError,
    BlueprintNotApprovedError,
    RetryExhaustedError,
    StatePersistenceError,
)
from core.models import AgentRole, Mission, MissionPhase, MissionStatus, RetryPolicy
from core.repository import MissionRepository
from core.state_log import StateLogManager

logger = logging.getLogger(__name__)

AgentCallable = Callable[[Mission], Awaitable[Mission]]

_PHASE_TO_AGENT: dict[MissionPhase, AgentRole] = {
    MissionPhase.THOR: AgentRole.THOR,
    MissionPhase.CAPTAIN_AMERICA: AgentRole.CAPTAIN_AMERICA,
    MissionPhase.IRON_CODER: AgentRole.IRON_CODER,
    MissionPhase.BLACK_WIDOW: AgentRole.BLACK_WIDOW,
    MissionPhase.INFILTRADO: AgentRole.INFILTRADO,
}


class NickFuryOrchestrator:
    """Orquestador central. Gestiona el ciclo de vida de misiones.

    Principio: Nick Fury no ejecuta — coordina y persiste.
    """

    def __init__(self, repo: MissionRepository, state_log: StateLogManager) -> None:
        self._repo = repo
        self._state_log = state_log

    async def create_mission(self, output_dir: str = "output/") -> Mission:
        """Crea y persiste una nueva misión con status=IDLE."""
        mission = Mission(output_dir=output_dir)
        await self._persist(mission)
        logger.info("Misión creada: %s", mission.mission_id)
        return mission

    async def dispatch(self, mission: Mission, agent: AgentRole, fn: AgentCallable) -> Mission:
        """Despacha al agente aplicando FURY RETRY LOGIC (backoff exponencial).

        Args:
            mission: estado actual de la misión.
            agent: rol del agente a ejecutar.
            fn: callable async que recibe Mission y retorna Mission actualizada.

        Raises:
            RetryExhaustedError: si se agotan los 3 reintentos.
        """
        mission.retry_policy = RetryPolicy()

        while True:
            try:
                mission = await fn(mission)
                mission.retry_policy = RetryPolicy()
                mission.status = MissionStatus.IN_PROGRESS
                mission.updated_at = datetime.now(timezone.utc)
                await self._persist(mission)
                return mission

            except AgentExecutionError as exc:
                if mission.retry_policy.is_exhausted:
                    mission.status = MissionStatus.FAILED
                    mission.updated_at = datetime.now(timezone.utc)
                    await self._persist(mission)
                    raise RetryExhaustedError(agent, mission.mission_id) from exc

                delay = mission.retry_policy.next_delay
                logger.warning(
                    "[%s] fallo intento %d — reintentando en %.1fs",
                    agent.value, mission.retry_policy.attempt, delay,
                )
                mission.retry_policy.attempt += 1
                await asyncio.sleep(delay)

    async def advance_phase(self, mission: Mission) -> Mission:
        """Avanza la fase en 1. Bloquea el paso 2→3 sin blueprint aprobado.

        Raises:
            BlueprintNotApprovedError: si intenta pasar de fase 2 a 3 sin aprobación.
        """
        next_phase_val = mission.current_phase.value + 1

        if (
            mission.current_phase == MissionPhase.CAPTAIN_AMERICA
            and (not mission.blueprint_ref or not mission.approved_by_human)
        ):
            raise BlueprintNotApprovedError(
                "El blueprint debe existir y ser aprobado por humano antes de Fase 3."
            )

        mission.current_phase = MissionPhase(next_phase_val)
        mission.updated_at = datetime.now(timezone.utc)
        await self._persist(mission)
        logger.info("Misión %s → fase %d", mission.mission_id, next_phase_val)
        return mission

    async def mark_awaiting_human(self, mission: Mission, reason: str) -> Mission:
        """Cambia status a AWAITING_HUMAN, registra reason en StateLog, persiste."""
        mission.status = MissionStatus.AWAITING_HUMAN
        mission.updated_at = datetime.now(timezone.utc)
        await self._state_log.append(
            mission,
            agent=AgentRole.NICK_FURY.value,
            event="awaiting_human",
            artifact=reason,
        )
        return mission

    async def resume_from_checkpoint(self, mission_id: str) -> Mission:
        """Recupera misión desde MongoDB. Verifica integridad del estado.

        Raises:
            ValueError: si la misión no existe.
        """
        mission = await self._repo.get_mission(mission_id)
        if mission is None:
            raise ValueError(f"Misión no encontrada: {mission_id}")

        if mission.status == MissionStatus.IN_PROGRESS and not mission.log:
            logger.warning("Misión %s: IN_PROGRESS con log vacío → FAILED", mission_id)
            mission.status = MissionStatus.FAILED
            mission.updated_at = datetime.now(timezone.utc)
            await self._persist(mission)

        return mission

    async def _persist(self, mission: Mission) -> None:
        """Persiste la misión. Si falla, lanza StatePersistenceError."""
        try:
            await self._repo.save_mission(mission)
        except Exception as exc:
            raise StatePersistenceError(str(exc)) from exc
