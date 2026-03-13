"""core/blueprint_schema.py — Modelos Pydantic v2 del Blueprint y del MAP.yaml.

Artefactos de salida de Captain America (Fase 2).
BlueprintV1: contrato técnico inmutable del producto a construir.
MissionMap: índice de fragmentación que rastrea cada archivo por agente y módulo.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.models import AgentRole

# ── Sub-modelos del Blueprint ─────────────────────────────────────────────────


class ApiEndpoint(BaseModel):
    method: str = Field(description="HTTP verb: GET | POST | PUT | DELETE | PATCH")
    path: str = Field(description="e.g. '/users/{user_id}'")
    description: str
    request_body: dict[str, Any] | None = None
    response_schema: dict[str, Any]
    auth_required: bool = False
    known_api: bool = True  # False → API-Fabricator debe crear conector


class DataModel(BaseModel):
    name: str = Field(description="PascalCase")
    fields: dict[str, str] = Field(description="{'field_name': 'type_annotation'}")
    db_collection: str | None = None  # None si no persiste


class ModuleSpec(BaseModel):
    module_name: str = Field(description="snake_case")
    responsibility: str = Field(max_length=100)
    estimated_lines: int = Field(gt=0, description="Hulk enforced en BlueprintV1 validator")
    depends_on: list[str] = []
    external_apis: list[str] = []


class AcceptanceCriterion(BaseModel):
    id: str = Field(description="e.g. 'AC-001'")
    description: str
    automated: bool = True  # True → debe tener test pytest


# ── Blueprint Principal ───────────────────────────────────────────────────────


class BlueprintV1(BaseModel):
    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    mission_id: str
    version: str = "1.0.0"
    product_name: str
    problem_statement: str
    target_audience: str
    tech_stack: list[str]
    modules: list[ModuleSpec]
    data_models: list[DataModel]
    api_endpoints: list[ApiEndpoint]
    acceptance_criteria: list[AcceptanceCriterion]
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)  # noqa: UP017
    )
    approved_by_human: bool = False

    @field_validator("modules")
    @classmethod
    def validate_no_module_exceeds_300(cls, v: list[ModuleSpec]) -> list[ModuleSpec]:
        for mod in v:
            if mod.estimated_lines > 300:
                raise ValueError(
                    f"Módulo '{mod.module_name}' supera 300L — Protocolo Hulk violado en Blueprint"
                )
        return v


# ── MAP.yaml Schema ───────────────────────────────────────────────────────────


class FileEntry(BaseModel):
    """Registro de un archivo creado por un agente."""

    path: str = Field(description="Ruta relativa desde raíz del proyecto")
    created_by: AgentRole
    module: str = Field(description="module_name del ModuleSpec correspondiente")
    responsibility: str = Field(description="Copia de ModuleSpec.responsibility")
    line_count: int | None = None  # Poblado por Hulk tras crear el archivo
    status: str = Field(
        default="pending",
        pattern="^(pending|created|refactored|deleted)$",
    )


class MissionMap(BaseModel):
    """Índice de fragmentación de una misión.

    Cap. América lo crea en Prompt #10. Nick Fury lo consulta en cada dispatch.
    Hulk lo actualiza con line_count tras crear cada archivo.
    """

    mission_id: str
    blueprint_id: str
    version: str = "1.0.0"
    files: list[FileEntry] = []
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)  # noqa: UP017
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)  # noqa: UP017
    )

    def get_files_by_agent(self, agent: AgentRole) -> list[FileEntry]:
        return [f for f in self.files if f.created_by == agent]

    def get_files_by_module(self, module_name: str) -> list[FileEntry]:
        return [f for f in self.files if f.module == module_name]

    def has_unknown_apis(self) -> bool:
        """True si algún endpoint en el blueprint referenciado tiene known_api=False."""
        return any(f.status != "deleted" for f in self.files if f.module == "__api_fabricator__")
