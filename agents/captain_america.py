"""agents/captain_america.py — Agente Capitán América: Generador de Blueprint y MAP.yaml.

Transforma el brief.yaml de Thor en un BlueprintV1 + MissionMap (Fase 2).
Auto-corrección: reintenta si el LLM viola el Protocolo Hulk (módulos > 300L).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import BaseModel, ValidationError

from core.blueprint_schema import BlueprintV1, FileEntry, MissionMap
from core.exceptions import AgentExecutionError
from core.llm_client import LLMClient, LLMRequest
from core.models import AgentRole, LogEntry, Mission
from tools.file_tools import safe_read_text, safe_write_text

logger = logging.getLogger(__name__)

_MAX_INTERNAL_RETRIES = 2


class CaptainAmericaAgent:
    """Traduce un brief.yaml (de Thor) en un BlueprintV1 + MissionMap.

    NO escribe código. Diseña contratos.
    """

    SYSTEM_PROMPT: ClassVar[str] = (
        "Eres un Arquitecto de Software Senior. Tu salida es SIEMPRE un JSON válido "
        "que conforma el schema BlueprintV1. Sin texto libre. Sin explicaciones.\n"
        "Reglas absolutas:\n"
        "- Ningún módulo puede tener estimated_lines > 300 (Protocolo Hulk).\n"
        "- Usa snake_case para module_name y PascalCase para DataModel.name.\n"
        "- Si el Blueprint requiere una API externa no documentada en el brief, "
        "marca el endpoint con known_api=false.\n"
        "- Cada AcceptanceCriterion debe tener automated=true a menos que sea UX subjetivo."
    )

    def __init__(self, llm_client: LLMClient, mission_root: Path) -> None:
        self._llm = llm_client
        self._mission_root = mission_root

    async def run(self, mission: Mission) -> Mission:
        """Orquesta: brief → blueprint → MAP. Actualiza refs en la misión.

        Raises:
            AgentExecutionError: si el LLM falla tras _MAX_INTERNAL_RETRIES.
        """
        brief_content = safe_read_text(
            mission.brief_ref or f"missions/{mission.mission_id}/brief.yaml"
        )
        blueprint = await self._extract_blueprint(brief_content, mission.mission_id)

        blueprint_path = f"missions/{mission.mission_id}/blueprint.yaml"
        map_path = f"missions/{mission.mission_id}/MAP.yaml"

        self._serialize_to_yaml(blueprint, blueprint_path)
        self._serialize_to_yaml(self._build_map_from_blueprint(blueprint), map_path)

        mission.blueprint_ref = blueprint_path
        mission.log.append(LogEntry(
            agent=AgentRole.CAPTAIN_AMERICA.value,
            event="blueprint_generated",
            artifact=blueprint_path,
        ))
        logger.info("[CaptainAmerica] Blueprint y MAP generados para %s", mission.mission_id)
        return mission

    async def _extract_blueprint(self, brief_content: str, mission_id: str) -> BlueprintV1:
        """Llama al LLM y parsea BlueprintV1. Reintenta si Pydantic rechaza la respuesta.

        Raises:
            AgentExecutionError: si todos los intentos fallan.
        """
        user_message = f"Genera el Blueprint para esta misión:\n\n{brief_content}"
        error_feedback: str | None = None

        for attempt in range(_MAX_INTERNAL_RETRIES + 1):
            if error_feedback:
                user_message = (
                    f"Tu respuesta anterior fue rechazada. Error:\n{error_feedback}\n\n"
                    f"Corrige y genera de nuevo el Blueprint:\n\n{brief_content}"
                )

            resp = await self._llm.complete(LLMRequest(
                role=AgentRole.CAPTAIN_AMERICA,
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                mission_id=mission_id,
            ))

            try:
                data = json.loads(resp.content)
                data.setdefault("blueprint_id", f"bp-{mission_id}")
                data.setdefault("mission_id", mission_id)
                return BlueprintV1(**data)
            except (json.JSONDecodeError, ValidationError) as exc:
                error_feedback = str(exc)
                log_path = f"missions/{mission_id}/blueprint_error_{attempt}.log"
                safe_write_text(log_path, f"Raw:\n{resp.content}\n\nError:\n{error_feedback}")
                logger.warning(
                    "[CaptainAmerica] intento %d/%d falló: %s",
                    attempt + 1, _MAX_INTERNAL_RETRIES + 1, error_feedback[:120],
                )

        raise AgentExecutionError(
            agent=AgentRole.CAPTAIN_AMERICA,
            reason=f"Falló tras {_MAX_INTERNAL_RETRIES + 1} intentos. Último: {error_feedback}",
            attempt=_MAX_INTERNAL_RETRIES + 1,
        )

    def _build_map_from_blueprint(self, blueprint: BlueprintV1) -> MissionMap:
        """Genera FileEntry 'pending' para cada módulo del Blueprint."""
        files: list[FileEntry] = []

        for mod in blueprint.modules:
            n = mod.module_name
            files += [
                FileEntry(
                    path=f"agents/{n}.py",
                    created_by=AgentRole.IRON_CODER,
                    module=n,
                    responsibility=mod.responsibility,
                ),
                FileEntry(
                    path=f"tools/{n}_tools.py",
                    created_by=AgentRole.IRON_CODER,
                    module=n,
                    responsibility=mod.responsibility,
                ),
                FileEntry(
                    path=f"tests/{n}/test_{n}.py",
                    created_by=AgentRole.IRON_CODER,
                    module=n,
                    responsibility=mod.responsibility,
                ),
            ]

        for ep in blueprint.api_endpoints:
            if not ep.known_api:
                slug = ep.path.strip("/").replace("/", "_")
                files.append(FileEntry(
                    path=f"tools/connectors/{slug}.py",
                    created_by=AgentRole.API_FABRICATOR,
                    module="__api_fabricator__",
                    responsibility=ep.description,
                ))

        return MissionMap(
            mission_id=blueprint.mission_id,
            blueprint_id=blueprint.blueprint_id,
            files=files,
        )

    def _serialize_to_yaml(self, model: BaseModel, path: str) -> None:
        """Serializa un modelo Pydantic a YAML en la ruta relativa dada."""
        safe_write_text(path, yaml.dump(model.model_dump(mode="json"), allow_unicode=True))
