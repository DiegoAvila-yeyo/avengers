# Prompt #14 — Vision-UI: Setup Atomic Design System

**Fase**: 3 — La Fábrica
**Agente objetivo**: Vision-UI
**Archivo(s) a crear**:
- `tools/ui_scaffold.py` — Scaffolder de estructura Atomic Design
- `docs/ui_style_guide.md` — Guía de estilos base (memoria de Vision-UI)
**Dependencias previas**: Prompt #10 (Blueprint aprobado por humano), Prompt #11 (file_tools)
**Checkpoint humano**: **[👤 HUMANO]** — Validar identidad visual y stack frontend antes de generar componentes

### 🔒 Enmienda AMD-01 Root Jail
Todo scaffolding de archivos frontend se escribe dentro del directorio del proyecto
via `file_tools.write_file()`. Ningún archivo se crea fuera del `project_root`.

---

## 📋 Prompt Completo

---

Actúa como un Senior Frontend Developer y UI Architect especializado en Atomic Design
y React/TypeScript, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → rol de Vision-UI, principio de escalabilidad.
3. Lee `core/blueprint_schema.py` → `BlueprintV1` para entender el producto a construir.
4. Lee `tools/file_tools.py` → `write_file` (ROOT JAIL).

---

### TAREA: Crear el scaffolder del Design System

#### ARCHIVO 1: `tools/ui_scaffold.py`

```python
# Estructura Atomic Design que Vision-UI genera por misión:
ATOMIC_STRUCTURE: Final[dict[str, list[str]]] = {
    "atoms":      ["Button", "Input", "Label", "Badge", "Spinner"],
    "molecules":  ["FormField", "SearchBar", "Card", "Alert"],
    "organisms":  ["Header", "DataTable", "Modal", "Sidebar"],
    "templates":  ["DashboardLayout", "AuthLayout", "LandingLayout"],
    "pages":      [],  # Poblado por el Blueprint de cada misión
}

class UIScaffolder:
    """
    Crea la estructura de carpetas y archivos base del Design System.
    Vision-UI llama este scaffolder antes de generar componentes específicos.
    """

    def __init__(self, file_tools: FileTools, project_root: Path): ...

    async def scaffold_project(
        self,
        mission_id: str,
        product_name: str,
        output_base: str = "output/{mission_id}/frontend",
    ) -> list[str]:
        """
        Crea la estructura de directorios Atomic Design:
          src/
            components/
              atoms/
              molecules/
              organisms/
            templates/
            pages/
            styles/
              tokens.css     ← Design tokens (colores, tipografía, spacing)
              globals.css
            lib/
              api.ts         ← Cliente HTTP para el backend FastAPI

        Retorna lista de rutas relativas creadas.
        Usa file_tools.write_file() para cada archivo. [ROOT JAIL activo]
        """

    async def generate_design_tokens(self, style_guide: "StyleGuide") -> str:
        """
        Genera tokens.css con variables CSS desde el StyleGuide.
        Formato:
          :root {
            --color-primary: #...; /* brand */
            --spacing-base: 8px;
            --font-body: 'Inter', sans-serif;
          }
        """

    async def generate_api_client(self, blueprint: BlueprintV1) -> str:
        """
        Genera lib/api.ts con funciones fetch tipadas para cada endpoint del Blueprint.
        Un método por ApiEndpoint. Usa fetch() nativo (no axios).
        """


class StyleGuide(BaseModel):
    """Memoria de Vision-UI: la guía de estilos del proyecto."""
    color_primary: str = "#3B82F6"    # Tailwind blue-500
    color_secondary: str = "#6B7280"
    color_danger: str = "#EF4444"
    color_success: str = "#10B981"
    font_body: str = "Inter"
    font_mono: str = "JetBrains Mono"
    spacing_base_px: int = 8
    border_radius: str = "0.5rem"
    dark_mode: bool = True
```

#### ARCHIVO 2: `docs/ui_style_guide.md`

Documenta:
- Paleta de colores con hex codes y uso semántico (primary, danger, success…).
- Tipografía: fuente, tamaños (xs/sm/md/lg/xl), pesos.
- Espaciado: grid de 8px, breakpoints (sm/md/lg/xl).
- Convenciones de naming de componentes React: `PascalCase`, props en `camelCase`.
- Convención de archivos: `ComponentName/index.tsx` + `ComponentName.test.tsx`.
- Regla Hulk para UI: ningún componente > 150 líneas. Si crece → extraer sub-componentes.

**Restricciones**:
- `tools/ui_scaffold.py` NO debe superar **120 líneas.**
- El scaffolder genera archivos vacíos/placeholder — Vision-UI Gen (Prompt #15) los rellena.
- `StyleGuide` se serializa a `missions/{id}/style_guide.yaml` via `file_tools`.

---

### TESTS REQUERIDOS: `tests/tools/test_ui_scaffold.py`

```python
# Test 1: scaffold_project crea estructura de directorios completa
async def test_scaffold_creates_atomic_structure(): ...

# Test 2: todos los writes via file_tools (ROOT JAIL)
async def test_scaffold_uses_file_tools_for_all_writes(): ...

# Test 3: generate_design_tokens produce CSS válido con variables
def test_generate_design_tokens_produces_css_variables(): ...

# Test 4: generate_api_client genera un método por ApiEndpoint
def test_api_client_has_method_per_endpoint(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `tools/ui_scaffold.py` < 120 líneas
- [ ] `docs/ui_style_guide.md` escrito con todas las secciones
- [ ] Estructura Atomic Design completa (atoms → pages)
- [ ] `generate_design_tokens` produce CSS con variables `:root`
- [ ] Todo I/O via `file_tools` (ROOT JAIL)
- [ ] 4 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | Todo scaffolding en `output/{mission_id}/frontend/` via `file_tools` |
| **Hulk UI** | Componentes React ≤ 150L — enforced en Style Guide |
| **Widow** | Tokens no usados en el Design System → eliminar |
