"""tools/feedback_analyzer.py — Análisis LLM de feedback (extraído de feedback_collector)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, ClassVar

import yaml

from tools.feedback_collector import FeedbackItem, FeedbackSummary
from tools.file_tools import write_file

if TYPE_CHECKING:
    from core.llm_client import LLMClient

logger = logging.getLogger(__name__)
_MAX_LLM_COMMENTS = 30


class FeedbackAnalyzer:
    """Analiza FeedbackItems via LLM y produce FeedbackSummary para Thor."""

    ANALYSIS_PROMPT: ClassVar[str] = (
        "Analiza comentarios de usuarios sobre un producto de software. "
        "Extrae: 1) Ratio de sentimiento positivo (float 0-1). "
        "2) Feature requests explícitas (list[str]). "
        "3) Nuevos dolores/problemas mencionados (list[str]). "
        "4) Una keyword concisa para la próxima búsqueda de Thor (str). "
        "Output: JSON con keys: positive_ratio, feature_requests, pain_points, "
        "suggested_keyword. Sin texto libre."
    )

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    async def analyze(
        self, items: list[FeedbackItem], mission_id: str
    ) -> FeedbackSummary:
        """Analiza top 30 comentarios via LLM y guarda feedback_summary.yaml."""
        from core.llm_client import LLMRequest
        from core.models import AgentRole

        top = sorted(items, key=lambda i: i.engagement, reverse=True)[:_MAX_LLM_COMMENTS]
        payload = [{"content": i.content, "engagement": i.engagement} for i in top]

        resp = await self._llm.complete(LLMRequest(
            role=AgentRole.INFILTRADO,
            system_prompt=self.ANALYSIS_PROMPT,
            user_message=json.dumps(payload, ensure_ascii=False),
            mission_id=mission_id,
        ))

        data = json.loads(resp.content)
        summary = FeedbackSummary(
            mission_id=mission_id,
            total_items=len(items),
            generated_at=datetime.now(tz=timezone.utc),  # noqa: UP017
            **data,
        )
        write_file(
            f"missions/{mission_id}/feedback_summary.yaml",
            yaml.dump(summary.model_dump(mode="json"), allow_unicode=True),
        )
        return summary
