"""agents/iron_coder.py — Agente Iron-Coder: Generador de módulos FastAPI.

Fase 3 — La Fábrica. Itera módulo a módulo (JIT context) sobre BlueprintV1
y delega a ApiFabricatorAgent cuando un endpoint tiene known_api=False (AMD-04).
Todo I/O pasa por file_tools — ROOT JAIL activo.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import yaml

from core.blueprint_schema import BlueprintV1, FileEntry, ModuleSpec
from core.exceptions import AgentExecutionError
from core.llm_client import LLMClient, LLMRequest
from core.models import AgentRole, LogEntry, Mission
from tools.file_tools import read_file, write_file
from tools.map_tools import add_file_entry, update_file_entry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class IronCoderAgent:
    """Genera módulos FastAPI a partir del BlueprintV1.

    Opera módulo a módulo (JIT context): un módulo = un LLM call.
    """

    SYSTEM_PROMPT: ClassVar[str] = (
        "Eres un Senior Backend Developer. Tu output es SIEMPRE código Python 3.12+ válido.\n"
        "Reglas absolutas:\n"
        "- FastAPI para endpoints. Pydantic v2 para schemas. Motor async para MongoDB.\n"
        "- Ningún archivo generado puede superar 300 líneas (Protocolo Hulk).\n"
        "  Si el módulo requiere más → divide en sub-módulos y documenta la división.\n"
        "- snake_case para funciones y variables. PascalCase para clases.\n"
        "- Manejo de errores: HTTPException con códigos correctos (400/404/422/500).\n"
        "- Incluye docstrings en todas las funciones públicas.\n"
        "- NO uses librerías fuera de pyproject.toml. Si necesitas una nueva → DETENTE."
    )

    def __init__(
        self,
        llm_client: LLMClient,
        api_fabricator: object,  # ApiFabricatorAgent — inyectado para AMD-04
        project_root: Path,
    ) -> None:
        self._llm = llm_client
        self._api_fabricator = api_fabricator
        self._project_root = project_root

    async def run(self, mission: Mission) -> Mission:
        """Itera sobre blueprint.modules y genera cada módulo en orden de dependencias.

        Para cada módulo:
        1. Detectar APIs desconocidas → delegar a ApiFabricatorAgent.
        2. Generar el módulo con el LLM (JIT: solo el módulo actual).
        3. Guardar con file_tools.write_file() [ROOT JAIL].
        4. Actualizar FileEntry en MAP.yaml (status=created, line_count).
        5. Registrar StateLogEntry en la misión.

        Raises:
            AgentExecutionError: si el LLM falla o Fabricator no puede resolver una API.
        """
        map_path = f"missions/{mission.mission_id}/MAP.yaml"
        blueprint = self._load_blueprint(mission)

        for module in blueprint.modules:
            unknown_apis = await self._check_unknown_apis(module, blueprint)
            if unknown_apis:
                await self._invoke_api_fabricator(unknown_apis, mission, map_path)

            code = await self._generate_module(module, blueprint, mission)
            file_path = f"{mission.output_dir}{mission.mission_id}/{module.module_name}.py"
            write_file(file_path, code)

            line_count = len(code.splitlines())
            update_file_entry(map_path, file_path, status="created", line_count=line_count)

            mission.log.append(LogEntry(
                agent=AgentRole.IRON_CODER.value,
                event="module_created",
                artifact=file_path,
            ))
            logger.info("[IronCoder] Módulo creado: %s (%d líneas)", file_path, line_count)

        return mission

    def _load_blueprint(self, mission: Mission) -> BlueprintV1:
        """Lee y deserializa el blueprint.yaml de la misión."""
        bp_path = mission.blueprint_ref or f"missions/{mission.mission_id}/blueprint.yaml"
        raw = read_file(bp_path)
        return BlueprintV1.model_validate(yaml.safe_load(raw))

    async def _check_unknown_apis(
        self, module: ModuleSpec, blueprint: BlueprintV1
    ) -> list[str]:
        """Retorna los nombres de APIs desconocidas que usa este módulo.

        Busca en blueprint.api_endpoints donde endpoint.module == module.module_name
        y endpoint.known_api == False. Complementa con module.external_apis.
        """
        unknown: list[str] = []
        for endpoint in blueprint.api_endpoints:
            # Detectar endpoints desconocidos que pertenecen a este módulo
            endpoint_module = getattr(endpoint, "module", None)
            if not endpoint.known_api and endpoint_module == module.module_name:
                unknown.append(endpoint.path)
        # También delegar si el módulo declara external_apis no conocidas
        for api_name in module.external_apis:
            if api_name not in unknown:
                unknown.append(api_name)
        return unknown

    async def _invoke_api_fabricator(
        self, api_names: list[str], mission: Mission, map_path: str
    ) -> list[Path]:
        """[API-FABRICATOR INVOCATION — AMD-04]

        Invoca ApiFabricatorAgent.generate_connector() para cada API desconocida.
        Actualiza MAP.yaml con los nuevos FileEntry.

        Raises:
            AgentExecutionError: si el Fabricator falla. Nick Fury gestiona el retry.
        """
        connector_paths: list[Path] = []
        for api_name in api_names:
            try:
                connector_path: Path = await self._api_fabricator.generate_connector(api_name)  # type: ignore[union-attr]
            except Exception as exc:
                raise AgentExecutionError(
                    AgentRole.IRON_CODER,
                    reason=f"ApiFabricator falló para '{api_name}': {exc}",
                    attempt=1,
                ) from exc

            connector_paths.append(connector_path)
            add_file_entry(
                map_path,
                FileEntry(
                    path=str(connector_path),
                    created_by=AgentRole.API_FABRICATOR,
                    module="__api_fabricator__",
                    responsibility=f"Conector externo para {api_name}",
                    status="created",
                ),
            )
            mission.log.append(LogEntry(
                agent=AgentRole.IRON_CODER.value,
                event="api_fabricator_invoked",
                artifact=str(connector_path),
            ))
        return connector_paths

    async def _generate_module(
        self, module: ModuleSpec, blueprint: BlueprintV1, mission: Mission
    ) -> str:
        """Llama al LLM con contexto JIT (solo el módulo actual).

        Raises:
            AgentExecutionError: si el LLM devuelve una respuesta vacía.
        """
        user_message = (
            f"Módulo a implementar:\n{module.model_dump_json(indent=2)}\n\n"
            f"Stack tecnológico: {', '.join(blueprint.tech_stack)}\n"
            f"Producto: {blueprint.product_name}\n"
            f"Genera SOLO el código Python del módulo '{module.module_name}'."
        )
        request = LLMRequest(
            role=AgentRole.IRON_CODER,
            system_prompt=self.SYSTEM_PROMPT,
            user_message=user_message,
            mission_id=mission.mission_id,
        )
        try:
            response = await self._llm.complete(request)
        except Exception as exc:
            raise AgentExecutionError(
                AgentRole.IRON_CODER,
                reason=f"LLM falló al generar módulo '{module.module_name}': {exc}",
                attempt=1,
            ) from exc

        if not response.content.strip():
            raise AgentExecutionError(
                AgentRole.IRON_CODER,
                reason=f"LLM devolvió respuesta vacía para módulo '{module.module_name}'",
                attempt=1,
            )
        return response.content
