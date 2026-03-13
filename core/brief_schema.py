"""core/brief_schema.py — Modelo de dominio BriefV1 (Pydantic v2).

Artefacto de salida de Thor. Alimenta a Captain America en Fase 2.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BriefV1(BaseModel):
    """Brief de mercado generado por Thor tras analizar señales públicas."""

    mission_id: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    pain_points: list[str] = Field(
        default_factory=list,
        description="Problemas detectados en las señales de mercado.",
    )
    opportunities: list[str] = Field(
        default_factory=list,
        description="Oportunidades de negocio identificadas.",
    )
    recommended_niche: str = Field(
        default="",
        description="Nicho de mercado recomendado por el análisis.",
    )
    keywords_expanded: list[str] = Field(
        default_factory=list,
        description="Keywords adicionales sugeridas por el LLM.",
    )
    raw_signal_count: int = Field(
        default=0,
        description="Total de señales recolectadas antes del filtrado.",
    )
