"""core/llm_client.py — Adaptador Universal LLM con gestión de presupuesto.

AMD-02 RETRY LOGIC: reintentos automáticos con backoff exponencial (2s / 4s / 8s).
Selecciona el modelo según AgentRole y registra tokens en el StateLog de la misión.

Uso:
    from core.llm_client import llm_client, LLMRequest, AgentRole
    response = await llm_client.complete(LLMRequest(
        role=AgentRole.IRON_CODER,
        system_prompt="Eres un experto en Python.",
        user_message="Escribe un hello world.",
        mission_id="mission-001",
    ))
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import anthropic
import openai
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from core.settings import settings
from tools.file_tools import safe_read_text, safe_write_text

logger = logging.getLogger(__name__)

# ── Modelos LLM ──────────────────────────────────────────────────────────────
_CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
_GPT_MODEL = "gpt-4o"

# AMD-02: 1 intento inicial + 3 reintentos → backoff 2s / 4s / 8s
_RETRY_ATTEMPTS = 4
_BACKOFF_MIN_S = 2
_BACKOFF_MAX_S = 8


# ── Enums y Modelos ──────────────────────────────────────────────────────────
class AgentRole(str, Enum):
    """Roles del pipeline AVENGERS. Determina qué LLM se invoca."""

    NICK_FURY = "nick_fury"
    THOR = "thor"
    CAPTAIN_AMERICA = "captain_america"
    IRON_CODER = "iron_coder"
    BLACK_WIDOW = "black_widow"
    INFILTRADO = "infiltrado"
    VISION_UI = "vision_ui"
    API_FABRICATOR = "api_fabricator"


# Claude para roles de código; GPT-4o para estrategia/orquestación.
_ROLE_TO_MODEL: dict[AgentRole, str] = {
    AgentRole.NICK_FURY: _GPT_MODEL,
    AgentRole.THOR: _GPT_MODEL,
    AgentRole.CAPTAIN_AMERICA: _GPT_MODEL,
    AgentRole.IRON_CODER: _CLAUDE_MODEL,
    AgentRole.BLACK_WIDOW: _CLAUDE_MODEL,
    AgentRole.INFILTRADO: _CLAUDE_MODEL,
    AgentRole.VISION_UI: _CLAUDE_MODEL,
    AgentRole.API_FABRICATOR: _CLAUDE_MODEL,
}

_CLAUDE_ROLES: frozenset[AgentRole] = frozenset(
    {
        AgentRole.IRON_CODER,
        AgentRole.BLACK_WIDOW,
        AgentRole.INFILTRADO,
        AgentRole.VISION_UI,
        AgentRole.API_FABRICATOR,
    }
)


class LLMRequest(BaseModel):
    """Petición a un LLM. Contrato de entrada para LLMClient.complete()."""

    role: AgentRole
    system_prompt: str
    user_message: str
    mission_id: str = Field(default="unassigned")
    max_tokens: int = Field(default=4096, ge=1, le=8192)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)


class TokenUsage(BaseModel):
    """Registro de uso de tokens de una llamada LLM."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMResponse(BaseModel):
    """Respuesta normalizada de cualquier proveedor LLM."""

    content: str
    model: str
    role: AgentRole
    usage: TokenUsage
    mission_id: str


# ── LLMClient ────────────────────────────────────────────────────────────────
class LLMClient:
    """Adaptador Universal LLM con retry logic (AMD-02) y token tracking.

    - Roles de código  (iron_coder, black_widow, infiltrado) → Claude.
    - Roles de estrategia (nick_fury, thor, captain_america)  → GPT-4o.
    """

    def __init__(self) -> None:
        self._openai = openai.AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )
        self._anthropic = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Envía la petición al LLM apropiado y registra el uso de tokens.

        Selecciona Anthropic o OpenAI según el AgentRole del request.
        AMD-02: los métodos internos reintentan hasta 3 veces (2s/4s/8s).
        """
        if request.role in _CLAUDE_ROLES:
            response = await self._complete_anthropic(request)
        else:
            response = await self._complete_openai(request)

        self._log_token_usage(response)
        return response

    @retry(
        stop=stop_after_attempt(_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=2, min=_BACKOFF_MIN_S, max=_BACKOFF_MAX_S),
        reraise=True,
    )
    async def _complete_openai(self, request: LLMRequest) -> LLMResponse:
        """Llama a la API de OpenAI. AMD-02: retry con backoff exponencial."""
        model = _ROLE_TO_MODEL[request.role]
        resp = await self._openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_message},
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        usage = resp.usage
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=model,
            role=request.role,
            usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
            mission_id=request.mission_id,
        )

    @retry(
        stop=stop_after_attempt(_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=2, min=_BACKOFF_MIN_S, max=_BACKOFF_MAX_S),
        reraise=True,
    )
    async def _complete_anthropic(self, request: LLMRequest) -> LLMResponse:
        """Llama a la API de Anthropic. AMD-02: retry con backoff exponencial."""
        model = _ROLE_TO_MODEL[request.role]
        resp = await self._anthropic.messages.create(
            model=model,
            system=request.system_prompt,
            messages=[{"role": "user", "content": request.user_message}],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        prompt_tokens = resp.usage.input_tokens
        completion_tokens = resp.usage.output_tokens
        return LLMResponse(
            content=resp.content[0].text if resp.content else "",
            model=model,
            role=request.role,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            mission_id=request.mission_id,
        )

    def _log_token_usage(self, response: LLMResponse) -> None:
        """Persiste el uso de tokens en el StateLog de la misión (AMD-05 placeholder).

        Escribe entradas JSONL en missions/<mission_id>-tokens.jsonl.
        TODO: reemplazar con repo.append_log() cuando StateLog repo esté disponible.
        """
        entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent": response.role.value,
            "event": "token_usage",
            "model": response.model,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        log_path = f"missions/{response.mission_id}-tokens.jsonl"
        try:
            existing = safe_read_text(log_path)
        except FileNotFoundError:
            existing = ""
        safe_write_text(log_path, existing + json.dumps(entry) + "\n")
        logger.debug("Token usage logged for mission %s: %s", response.mission_id, entry)


# Singleton — reutilizar conexiones HTTP entre llamadas.
llm_client = LLMClient()
