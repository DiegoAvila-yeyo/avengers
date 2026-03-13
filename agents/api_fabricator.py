"""agents/api_fabricator.py — API-Fabricator: genera conectores HTTP async (AMD-04).
Invocado por IronCoderAgent. Output: tools/connectors/{api_name}_connector.py [ROOT JAIL].
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import ClassVar

import httpx

from core.exceptions import AgentExecutionError, RootJailViolationError
from core.llm_client import LLMClient, LLMRequest
from core.models import AgentRole, LogEntry, Mission
from tools.file_tools import resolve_safe_path, write_file

logger = logging.getLogger(__name__)

_CONNECTORS_DIR = "tools/connectors"
_MAX_CONNECTOR_LINES = 250
_KNOWN_MODULES: frozenset[str] = frozenset([
    "os", "sys", "re", "json", "logging", "pathlib", "typing", "abc", "asyncio", "datetime",
    "enum", "functools", "collections", "contextlib", "io", "time", "uuid", "dataclasses", "copy",
    "math", "itertools", "__future__", "fastapi", "uvicorn", "pydantic", "httpx", "motor",
    "sqlalchemy", "asyncpg", "openai", "anthropic", "tenacity", "bs4", "lxml", "yaml", "dotenv",
])


class ApiFabricatorAgent:
    """Genera conectores Python async para APIs desconocidas.

    Invocado desde IronCoderAgent._invoke_api_fabricator(). Output: tools/connectors/.
    """

    CONNECTOR_SYSTEM_PROMPT: ClassVar[str] = (
        "Eres un experto en integración de APIs. Genera un conector Python async.\n"
        "Reglas: usa httpx.AsyncClient (no requests); captura HTTPStatusError; "
        "auth parametrizable via constructor; un método por endpoint en snake_case; "
        "type hints completos (Pydantic v2); conector stateless; ≤250L; solo código Python."
    )

    def __init__(self, llm_client: LLMClient, project_root: Path) -> None:
        self._llm = llm_client
        self._project_root = project_root

    async def generate_connector(
        self,
        api_name: str,
        docs_source: str,
        mission: Mission,
    ) -> Path:
        """Genera conector para api_name: fetch docs → LLM → split si >250L → write [ROOT JAIL].

        Raises:
            AgentExecutionError: si URL inaccesible o LLM falla.
        """
        docs_text = await self._fetch_docs(api_name, docs_source)
        code = await self._call_llm(api_name, docs_text, mission)

        if len(code.splitlines()) > _MAX_CONNECTOR_LINES:
            code = await self._request_split(api_name, code, mission)

        relative_path = f"{_CONNECTORS_DIR}/{api_name}_connector.py"
        target = resolve_safe_path(relative_path)
        write_file(relative_path, code)

        mission.log.append(LogEntry(
            agent=AgentRole.API_FABRICATOR.value,
            event="connector_generated", artifact=str(target),
        ))
        logger.info("[ApiFabricator] Conector generado: %s", target)
        return target

    async def validate_connector(self, connector_path: str) -> bool:
        """Valida sintaxis, imports conocidos, ≥1 método async y ROOT JAIL del conector.

        Raises:
            AgentExecutionError: si algún check falla.
        """
        try:
            safe = resolve_safe_path(connector_path)
        except RootJailViolationError as exc:
            raise AgentExecutionError(
                AgentRole.API_FABRICATOR,
                reason=f"ROOT JAIL violation: {exc}",
                attempt=1,
            ) from exc

        source = safe.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise AgentExecutionError(
                AgentRole.API_FABRICATOR,
                reason=f"Sintaxis inválida en conector: {exc}",
                attempt=1,
            ) from exc
        _validate_imports(source)
        _validate_has_async_methods(tree, connector_path)
        return True

    async def _fetch_docs(self, api_name: str, docs_source: str) -> str:
        """Obtiene texto de documentación. URL → httpx.get(); raw → directo."""
        if not docs_source.startswith(("http://", "https://")):
            return docs_source
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(docs_source)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as exc:
            raise AgentExecutionError(
                AgentRole.API_FABRICATOR,
                reason=f"URL inaccesible para '{api_name}': {exc}",
                attempt=1,
            ) from exc

    async def _call_llm(self, api_name: str, docs_text: str, mission: Mission) -> str:
        """Invoca el LLM para generar el conector."""
        request = LLMRequest(
            role=AgentRole.API_FABRICATOR,  # type: ignore[arg-type]
            system_prompt=self.CONNECTOR_SYSTEM_PROMPT,
            user_message=(
                f"Genera un conector Python async para la API '{api_name}'.\n"
                f"Documentación:\n{docs_text[:4000]}"
            ),
            mission_id=mission.mission_id,
        )
        try:
            response = await self._llm.complete(request)
        except Exception as exc:
            raise AgentExecutionError(
                AgentRole.API_FABRICATOR,
                reason=f"LLM falló al generar conector para '{api_name}': {exc}",
                attempt=1,
            ) from exc
        return response.content

    async def _request_split(self, api_name: str, code: str, mission: Mission) -> str:
        """Solicita al LLM refactorizar un conector que supera 250 líneas."""
        logger.warning("[ApiFabricator] Conector %s supera 250L → solicitando división", api_name)
        return await self._call_llm(
            api_name,
            f"El siguiente conector supera 250 líneas. "
            f"Refactorízalo para que quede en ≤250L manteniendo funcionalidad:\n\n{code}",
            mission,
        )


# ── Validadores auxiliares ────────────────────────────────────────────────────

def _validate_imports(source: str) -> None:
    """Lanza AgentExecutionError si el código importa módulos no conocidos."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".")[0]]
        else:
            continue
        for name in names:
            if name not in _KNOWN_MODULES:
                raise AgentExecutionError(
                    AgentRole.API_FABRICATOR,
                    reason=f"Import desconocido '{name}' no declarado en pyproject.toml",
                    attempt=1,
                )


def _validate_has_async_methods(tree: ast.AST, connector_path: str) -> None:
    """Lanza AgentExecutionError si el AST no tiene funciones async."""
    if not any(isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(tree)):
        raise AgentExecutionError(
            AgentRole.API_FABRICATOR,
            reason=f"Conector '{connector_path}' no tiene métodos async",
            attempt=1,
        )
