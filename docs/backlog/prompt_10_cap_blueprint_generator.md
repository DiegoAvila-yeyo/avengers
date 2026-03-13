# Prompt #10 — Cap. América: Generador de Blueprint + MAP.yaml

**Fase**: 2 — Equipo de Estrategia
**Agente objetivo**: Capitán América
**Archivo(s) a crear**:
- `agents/captain_america.py` — Agente generador de Blueprint y MAP.yaml
**Dependencias previas**: Prompt #09 (schemas), Prompt #08 (brief.yaml de Thor)
**Checkpoint humano**: **[👤 HUMANO]** — CRÍTICO: sin aprobación humana del Blueprint, la Fase 3 no inicia

### 🗺️ Enmienda: Cap's Map (v0.3.0)
- **[CAP'S MAP]** Al terminar, Cap. América debe escribir `missions/{mission_id}/MAP.yaml`
  con todos los `FileEntry` planificados (status="pending"). Nick Fury usará este MAP en
  cada dispatch para saber qué archivos se esperan y cuáles ya fueron creados.
  El MAP es obligatorio para avanzar a Fase 3. Nick Fury verifica su existencia en `advance_phase()`.

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en agentes LLM y generación de
artefactos estructurados, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolos Hulk y Widow.
2. Lee `ARCHITECTURE.md` → rol de Cap. América, formato de brief y blueprint.
3. Lee `core/blueprint_schema.py` → `BlueprintV1`, `MissionMap`, `FileEntry`, `ApiEndpoint`.
4. Lee `core/models.py` → `Mission`, `AgentRole`, `StateLogEntry`.

---

### TAREA: Implementar el agente Capitán América

#### ARCHIVO: `agents/captain_america.py`

```python
class CaptainAmericaAgent:
    """
    Traduce un brief.yaml (de Thor) en un BlueprintV1 + MissionMap.
    NO escribe código. Diseña contratos.
    """

    SYSTEM_PROMPT: ClassVar[str] = """
    Eres un Arquitecto de Software Senior. Tu salida es SIEMPRE un JSON válido
    que conforma el schema BlueprintV1. Sin texto libre. Sin explicaciones.
    Reglas absolutas:
    - Ningún módulo puede tener estimated_lines > 300 (Protocolo Hulk).
    - Usa snake_case para module_name y PascalCase para DataModel.name.
    - Si el Blueprint requiere una API externa no documentada en el brief,
      marca el endpoint con known_api=false.
    - Cada AcceptanceCriterion debe tener automated=true a menos que sea UX subjetivo.
    """

    def __init__(self, llm_client: "LLMClient", mission_root: Path): ...

    async def run(self, mission: Mission) -> Mission:
        """
        1. Leer brief.yaml desde mission.brief_ref.
        2. Llamar al LLM con SYSTEM_PROMPT + brief como user message.
        3. Parsear respuesta → BlueprintV1 (validación Pydantic automática).
        4. Serializar a YAML → guardar en missions/{mission_id}/blueprint.yaml.
        5. Generar MissionMap con FileEntry "pending" para cada módulo del Blueprint.
        6. Serializar MissionMap → guardar en missions/{mission_id}/MAP.yaml.
        7. Actualizar mission.blueprint_ref, agregar StateLogEntry, retornar.

        Si la validación Pydantic falla (ej: módulo > 300L):
        → Reintentar con el error como feedback al LLM (máx 2 reintentos internos).
        → Si sigue fallando → lanzar AgentExecutionError para que Fury active Retry Logic.
        """

    def _build_map_from_blueprint(self, blueprint: BlueprintV1, mission_id: str) -> MissionMap:
        """
        Genera los FileEntry "pending" para cada módulo del Blueprint.
        Convención de paths:
          - Backend: agents/{module_name}.py, tools/{module_name}_tools.py
          - Tests:   tests/{module_name}/test_{module_name}.py
        """

    def _serialize_to_yaml(self, model: BaseModel, path: Path) -> None:
        """Serializa un modelo Pydantic a YAML. Crea directorios si no existen."""
```

**Restricciones**:
- `CaptainAmericaAgent.run()` NO usa rutas absolutas. Todas las rutas son relativas
  a `mission_root` (el directorio raíz del proyecto). **[ROOT JAIL implícito]**
- Si el LLM devuelve JSON inválido → loggear el raw response en StateLog y relanzar.
- **Este archivo NO debe superar 200 líneas.** Si crece, extraer `_build_map_from_blueprint`
  a `tools/map_builder.py`.

---

### ARTEFACTOS GENERADOS POR ESTE AGENTE

```
missions/
└── {mission_id}/
    ├── brief.yaml          ← input (de Thor)
    ├── blueprint.yaml      ← output: BlueprintV1 serializado
    └── MAP.yaml            ← output: MissionMap con FileEntry "pending"
```

---

### TESTS REQUERIDOS: `tests/agents/test_captain_america.py`

```python
# Test 1: run() genera blueprint.yaml y MAP.yaml válidos
async def test_run_generates_blueprint_and_map(): ...

# Test 2: si LLM devuelve módulo > 300L → ValidationError → reintento interno
async def test_run_retries_on_hulk_violation(): ...

# Test 3: if LLM falla 2 veces → AgentExecutionError lanzado
async def test_run_raises_after_max_internal_retries(): ...

# Test 4: MAP.yaml contiene FileEntry "pending" para todos los módulos
def test_build_map_creates_pending_entries_for_all_modules(): ...

# Test 5: known_api=False en endpoint → FileEntry con external_apis marcado
def test_unknown_api_endpoint_reflected_in_map(): ...

# Test 6: blueprint.yaml guardado en ruta correcta (dentro de missions/)
async def test_blueprint_saved_in_correct_path(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `agents/captain_america.py` < 200 líneas
- [ ] `blueprint.yaml` y `MAP.yaml` escritos en `missions/{mission_id}/`
- [ ] Reintento interno (máx 2) si Pydantic rechaza el output del LLM
- [ ] `AgentExecutionError` lanzado si reintentos internos se agotan
- [ ] `MissionMap` con todos los `FileEntry` en status="pending"
- [ ] `known_api=False` reflejado correctamente en MAP
- [ ] 6 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Hulk** | `@field_validator` en BlueprintV1 rechaza módulos > 300L |
| **Widow** | Cero código muerto |
| **Cap's Map** | MAP.yaml es OBLIGATORIO para avanzar a Fase 3 |
| **Checkpoint** | Nick Fury leerá `approved_by_human` antes de despachar Iron-Coder |
