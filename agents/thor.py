"""agents/thor.py — Agente Thor: Investigación de Mercado.

Thor recolecta señales de fuentes públicas, extrae pain points y genera
el Brief (brief.yaml) que alimenta a Captain America en Fase 2.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import yaml

from core.brief_schema import BriefV1
from core.exceptions import AgentExecutionError
from core.llm_client import LLMClient, LLMRequest
from core.models import AgentRole, Mission
from tools.file_tools import safe_write_text
from tools.sources import PainSignal, SourceConnector

logger = logging.getLogger(__name__)

_TOP_SIGNALS = 20
_MAX_JSON_RETRIES = 2

_SYSTEM_PROMPT = "Eres un analista de mercado experto. Responde SIEMPRE con JSON válido, sin texto adicional."

_EXTRACTION_PROMPT = """\
Analiza las siguientes señales de Reddit, X y HackerNews y extrae un brief de mercado.

SEÑALES (ordenadas por engagement desc):
{signals_json}

Responde EXCLUSIVAMENTE con un objeto JSON con esta estructura exacta:
{{
  "pain_points": ["string", ...],
  "opportunities": ["string", ...],
  "recommended_niche": "string",
  "keywords_expanded": ["string", ...]
}}"""


class ThorAgent:
    """Agente Thor — Investigación y análisis de señales de mercado.

    Inyecta fuentes y LLMClient via constructor para facilitar testing.
    """

    def __init__(self, sources: list[SourceConnector], llm: LLMClient) -> None:
        self._sources = sources
        self._llm = llm

    async def run(self, mission: Mission) -> Mission:
        """Interfaz principal para Nick Fury. Orquesta recolección y extracción.

        Escribe missions/{id}/brief.yaml y actualiza mission.brief_ref.

        Raises:
            AgentExecutionError: si la extracción falla tras los reintentos.
        """
        keywords = ["saas", "startup", "automation", "pain point", "problem"]
        signals = await self._collect_signals(keywords)
        brief = await self._extract_brief(signals, mission.mission_id)

        rel_path = f"missions/{mission.mission_id}/brief.yaml"
        safe_write_text(rel_path, yaml.dump(brief.model_dump(mode="json"), allow_unicode=True))

        mission.brief_ref = rel_path
        logger.info("[Thor] Brief generado: %s (%d señales)", rel_path, len(signals))
        return mission

    async def _collect_signals(self, keywords: list[str]) -> list[PainSignal]:
        """Ejecuta búsquedas en paralelo en todas las fuentes inyectadas.

        Las excepciones individuales se logean y se ignoran (degradación elegante).
        """
        tasks = [src.search(keywords, limit=25) for src in self._sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        signals: list[PainSignal] = []
        for result in results:
            if isinstance(result, list):
                signals.extend(result)
            else:
                logger.warning("[Thor] Fuente falló: %s", result)

        return sorted(signals, key=lambda s: s.engagement, reverse=True)

    async def _extract_brief(self, signals: list[PainSignal], mission_id: str) -> BriefV1:
        """Filtra Top-20 señales por engagement y extrae brief via LLM.

        AMD-02: hasta _MAX_JSON_RETRIES reintentos si el LLM devuelve JSON inválido,
        pasando el error previo como feedback al modelo.

        Raises:
            AgentExecutionError: si persiste JSON inválido tras los reintentos.
        """
        top = signals[:_TOP_SIGNALS]
        signals_summary = [
            {"source": s.source, "content": s.content[:300], "engagement": s.engagement}
            for s in top
        ]
        base_msg = _EXTRACTION_PROMPT.format(signals_json=json.dumps(signals_summary, ensure_ascii=False))

        user_msg = base_msg
        last_error = ""

        for attempt in range(_MAX_JSON_RETRIES + 1):
            if attempt > 0:
                user_msg = f"ERROR PREVIO — corrige y responde solo JSON: {last_error}\n\n{base_msg}"

            resp = await self._llm.complete(LLMRequest(
                role=AgentRole.THOR,
                system_prompt=_SYSTEM_PROMPT,
                user_message=user_msg,
                mission_id=mission_id,
            ))

            try:
                data = json.loads(resp.content)
                return BriefV1(
                    mission_id=mission_id,
                    generated_at=datetime.now(tz=timezone.utc),
                    raw_signal_count=len(signals),
                    **data,
                )
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = str(exc)
                logger.warning("[Thor] JSON inválido (intento %d/%d): %s", attempt + 1, _MAX_JSON_RETRIES + 1, last_error)

        raise AgentExecutionError(
            AgentRole.THOR,
            f"JSON inválido tras {_MAX_JSON_RETRIES + 1} intentos: {last_error}",
            attempt=_MAX_JSON_RETRIES,
        )
