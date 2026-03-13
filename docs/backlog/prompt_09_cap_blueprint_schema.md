# Prompt #09 — Cap. América: Schema del Blueprint y MAP.yaml

**Fase**: 2 — Equipo de Estrategia
**Agente objetivo**: Capitán América
**Archivo(s) a crear**:
- `core/blueprint_schema.py` — Modelos Pydantic v2 del Blueprint y del MAP.yaml
**Dependencias previas**: Prompt #03 (modelos base), Prompt #08 (brief.yaml de Thor)
**Checkpoint humano**: No — continúa hacia Prompt #10

### 🗺️ Enmienda: Cap's Map (v0.3.0)
- **[CAP'S MAP]** Además del `blueprint.yaml`, Cap. América debe definir un `MAP.yaml`
  por misión. El MAP es el índice de fragmentación: registra qué archivos creó cada agente,
  en qué módulo viven y qué responsabilidad tienen. Previene que la IA pierda el rastro
  cuando la regla de 300 líneas fragmenta la lógica en múltiples archivos.

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en Pydantic v2 y diseño de contratos
de software, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → rol de Cap. América y formato del Blueprint.
3. Lee `core/models.py` → `AgentRole`, `MissionBlueprint` base.

---

### TAREA: Definir los schemas del Blueprint y el MAP.yaml

#### ARCHIVO: `core/blueprint_schema.py`

Define los siguientes modelos Pydantic v2:

```python
# ── Sub-modelos del Blueprint ─────────────────────────────────────

class ApiEndpoint(BaseModel):
    method: str                          # "GET" | "POST" | "PUT" | "DELETE" | "PATCH"
    path: str                            # e.g. "/users/{user_id}"
    description: str
    request_body: dict[str, Any] | None
    response_schema: dict[str, Any]
    auth_required: bool = False
    known_api: bool = True               # False → API-Fabricator debe crear conector

class DataModel(BaseModel):
    name: str                            # PascalCase
    fields: dict[str, str]               # {"field_name": "type_annotation"}
    db_collection: str | None            # None si no persiste

class ModuleSpec(BaseModel):
    module_name: str                     # snake_case
    responsibility: str                  # Una frase, ≤ 100 chars
    estimated_lines: int = Field(le=300) # Hulk enforced en schema
    depends_on: list[str] = []           # Otros module_names
    external_apis: list[str] = []        # Si non-empty → API-Fabricator invocado

class AcceptanceCriterion(BaseModel):
    id: str                              # "AC-001"
    description: str
    automated: bool = True               # Si True → debe tener test pytest

# ── Blueprint Principal ───────────────────────────────────────────

class BlueprintV1(BaseModel):
    model_config = ConfigDict(frozen=True)  # Inmutable una vez creado

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
    created_at: datetime
    approved_by_human: bool = False

    @field_validator("modules")
    @classmethod
    def validate_no_module_exceeds_300(cls, v: list[ModuleSpec]) -> list[ModuleSpec]:
        for mod in v:
            if mod.estimated_lines > 300:
                raise ValueError(f"Módulo '{mod.module_name}' supera 300L — Protocolo Hulk violado en Blueprint")
        return v

# ── MAP.yaml Schema ───────────────────────────────────────────────

class FileEntry(BaseModel):
    """Registro de un archivo creado por un agente."""
    path: str                        # Ruta relativa desde raíz del proyecto
    created_by: AgentRole
    module: str                      # module_name del ModuleSpec correspondiente
    responsibility: str              # Copia de ModuleSpec.responsibility
    line_count: int | None = None    # Poblado por Hulk después de crear el archivo
    status: str = "pending"          # "pending" | "created" | "refactored" | "deleted"

class MissionMap(BaseModel):
    """
    Índice de fragmentación de una misión.
    Cap. América lo crea en el Prompt #10. Nick Fury lo consulta en cada dispatch.
    Hulk lo actualiza con line_count tras crear cada archivo.
    """
    mission_id: str
    blueprint_id: str
    version: str = "1.0.0"
    files: list[FileEntry] = []
    created_at: datetime
    updated_at: datetime

    def get_files_by_agent(self, agent: AgentRole) -> list[FileEntry]:
        return [f for f in self.files if f.created_by == agent]

    def get_files_by_module(self, module_name: str) -> list[FileEntry]:
        return [f for f in self.files if f.module == module_name]

    def has_unknown_apis(self) -> bool:
        """True si algún FileEntry viene de un módulo con external_apis no vacíos."""
        ...
```

**Restricciones**:
- `BlueprintV1` es `frozen=True` — inmutable tras aprobación humana.
- `ApiEndpoint.known_api = False` es la señal que Iron-Coder usa para invocar al API-Fabricator.
- `MissionMap` debe ser serializable a YAML via `model.model_dump()` + PyYAML.
- **Este archivo NO debe superar 200 líneas.**

---

### TESTS REQUERIDOS: `tests/core/test_blueprint_schema.py`

```python
# Test 1: BlueprintV1 con módulo de 301L → ValidationError (Hulk enforced)
def test_blueprint_rejects_module_over_300_lines(): ...

# Test 2: BlueprintV1 frozen → no permite mutación post-creación
def test_blueprint_is_immutable(): ...

# Test 3: MissionMap.get_files_by_agent filtra correctamente
def test_mission_map_get_files_by_agent(): ...

# Test 4: ApiEndpoint.known_api=False serializa correctamente para Iron-Coder
def test_unknown_api_endpoint_serializes(): ...

# Test 5: MissionMap serializable a dict (para YAML export)
def test_mission_map_serializable_to_dict(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `core/blueprint_schema.py` < 200 líneas
- [ ] `BlueprintV1` frozen e inmutable
- [ ] `@field_validator` rechaza módulos > 300L
- [ ] `MissionMap` con métodos de consulta por agente y módulo
- [ ] `ApiEndpoint.known_api` como señal para API-Fabricator
- [ ] 5 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Hulk** (> 300L) | Enforced en `@field_validator` — Blueprint rechazado si viola |
| **Widow** | Cero código muerto |
| **Cap's Map** | `MissionMap` es obligatorio — sin MAP no hay dispatch a Fase 3 |
