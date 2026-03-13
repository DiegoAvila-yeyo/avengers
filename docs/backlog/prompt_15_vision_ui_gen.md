# Prompt #15 — Vision-UI Generator: Componentes React desde Blueprint

**Fase**: 3 — La Fábrica
**Agente objetivo**: Vision-UI
**Archivo(s) a crear**:
- `agents/vision_ui.py` — Agente generador de componentes React
**Dependencias previas**: Prompt #14 (UIScaffolder, StyleGuide), Prompt #10 (Blueprint)
**Checkpoint humano**: No

### 🔒 Enmienda AMD-01 Root Jail
Todos los componentes React generados se escriben en
`output/{mission_id}/frontend/src/` via `file_tools.write_file()`.
Nunca fuera del project_root.

---

## 📋 Prompt Completo

---

Actúa como un Senior Frontend Developer especializado en React, TypeScript y Atomic
Design, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `docs/ui_style_guide.md` → paleta, tipografía, convenciones de naming.
3. Lee `core/blueprint_schema.py` → `BlueprintV1`, `ApiEndpoint`, `DataModel`.
4. Lee `tools/ui_scaffold.py` → `ATOMIC_STRUCTURE`, `StyleGuide`.
5. Lee `tools/file_tools.py` → `write_file` (ROOT JAIL).

---

### TAREA: Implementar el agente Vision-UI

#### ARCHIVO: `agents/vision_ui.py`

```python
class VisionUIAgent:
    """
    Genera componentes React TypeScript siguiendo Atomic Design.
    Opera componente a componente (JIT context).
    La Style Guide es su memoria permanente — siempre la inyecta en el prompt.
    """

    COMPONENT_PROMPT: ClassVar[str] = """
    Eres un Senior Frontend Developer. Genera un componente React TypeScript.
    Reglas absolutas:
    - TypeScript estricto: no 'any', interfaces explícitas para todas las props.
    - Tailwind CSS para estilos — sin CSS-in-JS, sin styled-components.
    - Componentes funcionales con hooks — sin class components.
    - Accesibilidad: atributos ARIA en elementos interactivos.
    - LÍMITE: 150 líneas máximo por componente (Protocolo Hulk UI).
      Si supera → divide en sub-componentes del mismo nivel atómico.
    - Naming: PascalCase para componente, camelCase para props.
    - Exportar como named export + default export.
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        scaffolder: UIScaffolder,
        file_tools: FileTools,
        project_root: Path,
    ): ...

    async def run(self, mission: Mission) -> Mission:
        """
        1. Leer blueprint.yaml y style_guide.yaml de la misión.
        2. Llamar scaffolder.scaffold_project() si no existe la estructura.
        3. Por cada DataModel en el Blueprint → generar componentes CRUD:
           - atoms: campos de formulario específicos del modelo.
           - molecules: tarjeta de visualización del modelo.
           - organisms: tabla y formulario completo.
        4. Por cada página inferida del Blueprint → generar template + page.
        5. Actualizar MAP.yaml con los FileEntry creados.
        6. Registrar StateLogEntry y retornar misión.
        """

    async def _generate_component(
        self,
        component_name: str,
        atomic_level: str,           # "atoms" | "molecules" | "organisms" | "templates" | "pages"
        context: dict[str, Any],     # DataModel o ApiEndpoint relevante — JIT
        style_guide: StyleGuide,
        mission_id: str,
    ) -> Path:
        """
        Genera un componente React con el LLM.
        Contexto JIT: solo el DataModel/endpoint relevante + StyleGuide.
        Guarda en output/{mission_id}/frontend/src/components/{level}/{name}/index.tsx.
        Si el archivo generado supera 150L → solicitar split al LLM.
        """

    async def _generate_page(
        self,
        page_name: str,
        endpoints: list["ApiEndpoint"],
        style_guide: StyleGuide,
        mission_id: str,
    ) -> Path:
        """
        Genera una página completa que compone organisms.
        Guarda en output/{mission_id}/frontend/src/pages/{page_name}.tsx.
        """
```

**Restricciones**:
- El prompt LLM incluye **solo** el DataModel o ApiEndpoint del componente actual (JIT).
  No inyectar el Blueprint completo.
- Tailwind CSS obligatorio — sin `style={}` inline ni CSS modules.
- **Este archivo NO debe superar 200 líneas.** Si crece, extraer `_generate_page` a `tools/ui_generator.py`.

---

### TESTS REQUERIDOS: `tests/agents/test_vision_ui.py`

```python
# Test 1: run() genera componentes para cada DataModel del Blueprint
async def test_run_generates_components_for_data_models(): ...

# Test 2: componente > 150L → LLM solicitado a dividir (Hulk UI)
async def test_oversized_component_triggers_split(): ...

# Test 3: todos los writes via file_tools (ROOT JAIL)
async def test_all_writes_use_file_tools(): ...

# Test 4: MAP.yaml actualizado con FileEntry de cada componente
async def test_map_updated_with_component_entries(): ...

# Test 5: StyleGuide inyectada en cada LLM call
async def test_style_guide_injected_in_every_prompt(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `agents/vision_ui.py` < 200 líneas
- [ ] Componentes en `output/{id}/frontend/src/` via `file_tools`
- [ ] JIT: solo DataModel/endpoint actual en cada LLM call
- [ ] Hulk UI: componentes > 150L → split solicitado
- [ ] MAP.yaml actualizado
- [ ] 5 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | Output en `output/{mission_id}/frontend/` via `file_tools` |
| **Hulk UI** | 150L máximo por componente React |
| **JIT Context** | Solo DataModel/endpoint relevante por LLM call |
| **Widow** | Cero componentes generados sin uso confirmado en Blueprint |
