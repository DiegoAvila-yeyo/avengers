"""core/models.py — Modelos de dominio compartidos (Pydantic v2).

Define Mission y sus tipos asociados: MissionStatus, MissionPhase, LogEntry.
Estos modelos son la fuente de verdad para el State Log descrito en ARCHITECTURE.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


# ── Enumeraciones ─────────────────────────────────────────────────────────────


class MissionStatus(str, Enum):
    """Estados posibles de una misión en el pipeline AVENGERS."""

    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    FAILED = "failed"


class MissionPhase(int, Enum):
    """Fases del Bucle Infinito. Cada valor mapea a un agente."""

    THOR = 1
    CAPTAIN_AMERICA = 2
    IRON_CODER = 3
    BLACK_WIDOW = 4
    INFILTRADO = 5


# ── Sub-modelos ───────────────────────────────────────────────────────────────


class LogEntry(BaseModel):
    """Entrada individual del State Log de una misión (TTL: últimas 50)."""

    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent: str = Field(description="Nombre del agente que generó el evento.")
    event: str = Field(description="Tipo de evento (e.g. 'brief_generated').")
    artifact: str | None = Field(
        default=None,
        description="Ruta al artefacto producido, si aplica.",
    )


# ── Modelo Principal ──────────────────────────────────────────────────────────


class Mission(BaseModel):
    """Representación completa de una misión.

    Actúa como State Log compartido entre agentes (Protocolo JIT).
    Se persiste en MongoDB mediante MissionRepository (AMD-05).
    """

    mission_id: str = Field(
        default_factory=lambda: f"mission-{uuid.uuid4().hex[:8]}",
        description="Identificador único de la misión.",
    )
    status: MissionStatus = Field(default=MissionStatus.IDLE)
    current_phase: MissionPhase = Field(default=MissionPhase.THOR)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    brief_ref: str | None = Field(
        default=None,
        description="Ruta al brief.yaml generado por Thor.",
    )
    blueprint_ref: str | None = Field(
        default=None,
        description="Ruta al blueprint.yaml generado por Captain America.",
    )
    log: list[LogEntry] = Field(
        default_factory=list,
        description="Historial de eventos (máx. 50 entradas, TTL gestionado por repo).",
    )
