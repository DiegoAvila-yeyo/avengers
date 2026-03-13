"""tools/code_splitter.py — Fragmentación semántica de archivos via LLM.

Extraído de BlackWidowAgent para mantener agents/black_widow.py < 220 líneas.
Usa el LLM para decidir límites de separación semánticos (no mecánicos).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tools.file_tools import write_file

if TYPE_CHECKING:
    from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

_MAX_SUB_MODULE_LINES = 280

_SYSTEM_PROMPT = (
    "Eres un experto en refactorización Python. Divide el archivo recibido en "
    "sub-módulos con responsabilidad única, cada uno ≤ 280 líneas. "
    "Responde SOLO con JSON válido:\n"
    '{"modules": [{"filename": "...", "content": "..."}], '
    '"stub_content": "...imports y re-exports del original..."}'
)


async def split_file_semantically(
    file_path: str,
    content: str,
    llm_client: LLMClient,
    mission_id: str = "splitter",
) -> list[str]:
    """Divide un archivo en sub-módulos usando el LLM para decidir límites semánticos.

    Args:
        file_path:  Ruta relativa del archivo a dividir.
        content:    Contenido actual del archivo.
        llm_client: Instancia de LLMClient para llamadas LLM.
        mission_id: ID de misión para trazabilidad en el log LLM.

    Returns:
        Lista de rutas relativas de sub-módulos creados.
    """
    from core.llm_client import AgentRole as LLMAgentRole
    from core.llm_client import LLMRequest

    base_dir = str(Path(file_path).parent)
    stem = Path(file_path).stem

    request = LLMRequest(
        role=LLMAgentRole.BLACK_WIDOW,
        system_prompt=_SYSTEM_PROMPT,
        user_message=(
            f"Archivo: {file_path}\n"
            f"Usa prefijo '{stem}_' para los sub-módulos.\n\n"
            f"```python\n{content}\n```"
        ),
        mission_id=mission_id,
    )

    response = await llm_client.complete(request)

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        logger.warning("code_splitter: LLM devolvió JSON inválido; split omitido.")
        return []

    created: list[str] = []
    for module in data.get("modules", []):
        filename = module.get("filename", "")
        module_content = module.get("content", "")
        if not filename or not module_content:
            continue
        sub_path = f"{base_dir}/{filename}" if base_dir not in (".", "") else filename
        lines = len(module_content.splitlines())
        if lines > _MAX_SUB_MODULE_LINES:
            logger.warning(
                "code_splitter: %s tiene %d líneas (> %d).",
                sub_path, lines, _MAX_SUB_MODULE_LINES,
            )
        write_file(sub_path, module_content)
        created.append(sub_path)

    stub = data.get("stub_content", "")
    if stub and created:
        write_file(file_path, stub)

    return created
