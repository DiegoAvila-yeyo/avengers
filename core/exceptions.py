"""core/exceptions.py — Excepciones del sistema AVENGERS.

Jerarquía: todas heredan de AvengersBaseError para facilitar catching genérico.
"""

from __future__ import annotations

from core.models import AgentRole


class AvengersBaseError(Exception):
    """Excepción base del sistema AVENGERS."""


class StatePersistenceError(AvengersBaseError):
    """Fallo al sincronizar el State Log con MongoDB."""


class AgentExecutionError(AvengersBaseError):
    """Un agente terminó con error no recuperable."""

    def __init__(self, agent: AgentRole, reason: str, attempt: int) -> None:
        self.agent = agent
        self.reason = reason
        self.attempt = attempt
        super().__init__(f"[{agent.value}] attempt={attempt}: {reason}")


class RetryExhaustedError(AvengersBaseError):
    """Nick Fury agotó los 3 reintentos de un agente."""

    def __init__(self, agent: AgentRole, mission_id: str) -> None:
        self.agent = agent
        self.mission_id = mission_id
        super().__init__(
            f"Reintentos agotados para {agent.value} en misión {mission_id}"
        )


class BlueprintNotApprovedError(AvengersBaseError):
    """Se intentó ejecutar Fase 3 sin Blueprint aprobado por humano."""


class RootJailViolationError(AvengersBaseError):
    """Un tool intentó acceder a una ruta fuera del proyecto. [ROOT JAIL]"""
