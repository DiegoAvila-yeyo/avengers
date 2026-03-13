"""agents/vision_ui.py — Vision-UI: Generador de componentes React desde Blueprint.

Fase 3 — La Fábrica. Opera componente a componente (JIT context) sobre BlueprintV1.
Todo I/O pasa por file_tools — ROOT JAIL AMD-01 activo.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, ClassVar

import yaml

from core.blueprint_schema import ApiEndpoint, BlueprintV1, FileEntry
from core.exceptions import AgentExecutionError
from core.llm_client import LLMClient, LLMRequest
from core.models import AgentRole, LogEntry, Mission
from tools.file_tools import read_file
from tools.map_tools import add_file_entry
from tools.ui_scaffold import FileTools, StyleGuide, UIScaffolder

logger = logging.getLogger(__name__)

# atoms/molecules/organisms to generate per DataModel — {name} = model.name
_ATOMIC_MAP: dict[str, list[str]] = {
    "atoms": ["{name}Field"],
    "molecules": ["{name}Card"],
    "organisms": ["{name}Table", "{name}Form"],
}


class VisionUIAgent:
    """Genera componentes React TypeScript (Atomic Design) desde el BlueprintV1.

    Opera componente a componente (JIT context): un componente = un LLM call.
    La StyleGuide es inyectada en cada prompt (memoria permanente del agente).
    """

    COMPONENT_PROMPT: ClassVar[str] = (
        "Eres un Senior Frontend Developer. Genera un componente React TypeScript.\n"
        "Reglas absolutas:\n"
        "- TypeScript estricto: no 'any', interfaces explícitas para todas las props.\n"
        "- Tailwind CSS para estilos — sin CSS-in-JS, sin styled-components.\n"
        "- Componentes funcionales con hooks — sin class components.\n"
        "- Accesibilidad: atributos ARIA en elementos interactivos.\n"
        "- LÍMITE: 150 líneas máximo por componente (Protocolo Hulk UI).\n"
        "  Si supera → divide en sub-componentes del mismo nivel atómico.\n"
        "- Naming: PascalCase para componente, camelCase para props.\n"
        "- Exportar como named export + default export."
    )

    def __init__(
        self,
        llm_client: LLMClient,
        scaffolder: UIScaffolder,
        file_tools: FileTools,
        project_root: Path,
    ) -> None:
        self._llm = llm_client
        self._scaffolder = scaffolder
        self._ft = file_tools
        self._project_root = project_root

    async def run(self, mission: Mission) -> Mission:
        """Genera componentes React para cada DataModel y página del Blueprint.

        1. Lee blueprint.yaml de la misión.
        2. Scaffolda el proyecto si no existe la estructura.
        3. Por cada DataModel → genera atoms, molecules, organisms (JIT).
        4. Por cada página inferida del Blueprint → genera page component.
        5. Actualiza MAP.yaml con FileEntry de cada componente creado.
        6. Registra StateLogEntry y retorna la misión.
        """
        blueprint = self._load_blueprint(mission)
        style_guide = self._load_style_guide(mission)
        map_path = f"missions/{mission.mission_id}/MAP.yaml"

        await self._scaffolder.scaffold_project(mission.mission_id)

        for model in blueprint.data_models:
            for level, templates in _ATOMIC_MAP.items():
                for tmpl in templates:
                    name = tmpl.format(name=model.name)
                    path = await self._generate_component(
                        name, level, model.model_dump(), style_guide, mission.mission_id
                    )
                    self._register(mission, map_path, str(path), f"React {level} for {model.name}")

        pages = {ep.path.split("/")[1] for ep in blueprint.api_endpoints if ep.path.count("/") >= 1}
        for page in sorted(pages):
            path = await self._generate_page(
                page.capitalize(), blueprint.api_endpoints, style_guide, mission.mission_id
            )
            self._register(mission, map_path, str(path), f"Page for /{page}")

        return mission

    async def _generate_component(
        self,
        component_name: str,
        atomic_level: str,
        context: dict[str, Any],
        style_guide: StyleGuide,
        mission_id: str,
    ) -> Path:
        """Genera un componente React con el LLM (JIT: solo context del modelo actual).

        Si el output supera 150 líneas → solicita split al LLM (Hulk UI).
        Guarda en output/{mission_id}/frontend/src/components/{level}/{name}/index.tsx.
        """
        user_msg = (
            f"StyleGuide: {style_guide.model_dump_json()}\n"
            f"Nivel atómico: {atomic_level}\n"
            f"Contexto JIT (DataModel): {context}\n"
            f"Genera el componente React TypeScript '{component_name}'."
        )
        content = await self._call_llm(user_msg, mission_id)
        if len(content.splitlines()) > 150:
            content = await self._request_split(component_name, content, mission_id)

        rel = (
            f"output/{mission_id}/frontend/src/components"
            f"/{atomic_level}/{component_name}/index.tsx"
        )
        self._ft.write_file(rel, content)
        return Path(rel)

    async def _generate_page(
        self,
        page_name: str,
        endpoints: list[ApiEndpoint],
        style_guide: StyleGuide,
        mission_id: str,
    ) -> Path:
        """Genera una página que compone organisms (JIT: solo endpoints relevantes).

        Guarda en output/{mission_id}/frontend/src/pages/{page_name}.tsx.
        """
        eps = [{"method": e.method, "path": e.path} for e in endpoints]
        user_msg = (
            f"StyleGuide: {style_guide.model_dump_json()}\n"
            f"Endpoints JIT: {eps}\n"
            f"Genera la página React TypeScript '{page_name}Page' componiendo organisms."
        )
        content = await self._call_llm(user_msg, mission_id)
        rel = f"output/{mission_id}/frontend/src/pages/{page_name}.tsx"
        self._ft.write_file(rel, content)
        return Path(rel)

    async def _call_llm(self, user_message: str, mission_id: str) -> str:
        """Realiza un LLM call con el COMPONENT_PROMPT como system prompt."""
        request = LLMRequest(
            role=AgentRole.VISION_UI,
            system_prompt=self.COMPONENT_PROMPT,
            user_message=user_message,
            mission_id=mission_id,
        )
        try:
            response = await self._llm.complete(request)
        except Exception as exc:
            raise AgentExecutionError(
                AgentRole.VISION_UI, reason=str(exc), attempt=1
            ) from exc
        if not response.content.strip():
            raise AgentExecutionError(
                AgentRole.VISION_UI, reason="LLM devolvió respuesta vacía", attempt=1
            )
        return response.content

    async def _request_split(self, name: str, content: str, mission_id: str) -> str:
        """Solicita al LLM que divida un componente > 150 líneas (Protocolo Hulk UI)."""
        return await self._call_llm(
            f"El componente '{name}' supera 150 líneas (Protocolo Hulk UI).\n"
            f"Divide en sub-componentes. Genera SOLO el principal refactorizado (<=150L):\n"
            f"{content}",
            mission_id,
        )

    def _load_blueprint(self, mission: Mission) -> BlueprintV1:
        """Lee y deserializa el blueprint.yaml de la misión."""
        bp_path = mission.blueprint_ref or f"missions/{mission.mission_id}/blueprint.yaml"
        return BlueprintV1.model_validate(yaml.safe_load(read_file(bp_path)))

    def _load_style_guide(self, mission: Mission) -> StyleGuide:
        """Lee style_guide.yaml si existe; retorna StyleGuide por defecto si no."""
        sg_path = f"missions/{mission.mission_id}/style_guide.yaml"
        try:
            return StyleGuide.model_validate(yaml.safe_load(read_file(sg_path)))
        except FileNotFoundError:
            return StyleGuide()

    def _register(
        self, mission: Mission, map_path: str, path: str, responsibility: str
    ) -> None:
        """Añade FileEntry al MAP.yaml y registra StateLogEntry."""
        add_file_entry(
            map_path,
            FileEntry(
                path=path,
                created_by=AgentRole.VISION_UI,
                module="vision_ui",
                responsibility=responsibility,
                status="created",
            ),
        )
        mission.log.append(LogEntry(
            agent=AgentRole.VISION_UI.value,
            event="component_created",
            artifact=path,
        ))
        logger.info("[VisionUI] Componente creado: %s", path)
