"""tools/sources/__init__.py — Interfaz común de los conectores de Thor (Prompt #07)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class PainSignal(BaseModel):
    """Señal de dolor detectada en una fuente de datos pública."""

    source: str          # "reddit" | "x" | "hackernews"
    content: str         # Texto del post/comentario/pregunta
    url: str
    engagement: int      # Upvotes, likes, puntos — proxy de relevancia
    author: str
    collected_at: datetime
    keywords: list[str]  # Tags o flair detectados


@runtime_checkable
class SourceConnector(Protocol):
    """Protocolo común para todos los conectores de fuentes de Thor."""

    async def search(self, keywords: list[str], limit: int) -> list[PainSignal]: ...
    async def get_trending(self, category: str, limit: int) -> list[PainSignal]: ...
