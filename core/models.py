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
    AWAITING_HUMAN = "awaiting_human"
    REVIEW = "review"
    DONE = "done"
    FAILED = "failed"
    ABORTED = "aborted"


class MissionPhase(int, Enum):
    """Fases del Bucle Infinito. Cada valor mapea a un agente."""

    THOR = 1
    CAPTAIN_AMERICA = 2
    IRON_CODER = 3
    BLACK_WIDOW = 4
    INFILTRADO = 5


class AgentRole(str, Enum):
    """Roles de agentes del sistema AVENGERS."""

    NICK_FURY = "nick_fury"
    THOR = "thor"
    CAPTAIN_AMERICA = "captain_america"
    IRON_CODER = "iron_coder"
    BLACK_WIDOW = "black_widow"
    INFILTRADO = "infiltrado"
    VISION_UI = "vision_ui"
    API_FABRICATOR = "api_fabricator"
    HULK = "hulk"


class RetryPolicy(BaseModel):
    """Política de reintentos exponencial para Nick Fury dispatcher."""

    max_attempts: int = Field(default=3, ge=1, description="Máximo de intentos.")
    base_delay: float = Field(default=2.0, gt=0, description="Delay base en segundos.")
    attempt: int = Field(default=0, ge=0, description="Intento actual (0-indexed).")

    @property
    def is_exhausted(self) -> bool:
        """True si ya se alcanzó el máximo de intentos."""
        return self.attempt >= self.max_attempts

    @property
    def next_delay(self) -> float:
        """Delay exponencial para el siguiente intento: base_delay * 2^attempt."""
        return self.base_delay * (2 ** self.attempt)


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
    approved_by_human: bool = Field(
        default=False,
        description="True cuando un humano aprobó el blueprint (checkpoint fase 2→3).",
    )
    retry_policy: RetryPolicy = Field(
        default_factory=RetryPolicy,
        description="Política de reintentos para el dispatcher de Nick Fury.",
    )
    output_dir: str = Field(
        default="output/",
        description="Directorio de destino para los artefactos finales.",
    )
