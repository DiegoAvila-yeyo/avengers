# Prompt #19 — Black Widow: Fragmentador Automático y Refactorizador

**Fase**: 4 — Sistema de Calidad
**Agente objetivo**: Black Widow
**Archivo(s) a crear**:
- `agents/black_widow.py` — Agente refactorizador: fragmenta archivos masivos y limpia código muerto
**Dependencias previas**: Prompt #17 (HulkAgent, GuardrailReport), Prompt #11 (file_tools)
**Checkpoint humano**: No

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en refactorización de código y
análisis estático, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → Protocolo Widow (el que implementas aquí).
2. Lee `ARCHITECTURE.md` → rol de Black Widow como The Cleaner.
3. Lee `agents/hulk.py` → `GuardrailReport`, `GuardrailViolation`, `ViolationType`.
4. Lee `tools/file_tools.py` → `read_file`, `write_file`, `count_lines`.
5. Lee `tools/shell_tools.py` → `run_command` (para ruff --fix).

---

### TAREA: Implementar el agente Black Widow

#### ARCHIVO: `agents/black_widow.py`

```python
class RefactorAction(BaseModel):
    """Registro de una acción de refactorización aplicada."""
    file_path: str
    action_type: str     # "split" | "remove_dead_code" | "fix_imports" | "rename"
    description: str
    lines_before: int
    lines_after: int


class WidowReport(BaseModel):
    """Resumen del trabajo de Black Widow en una misión."""
    mission_id: str
    actions: list[RefactorAction]
    files_split: int
    dead_code_removed: int    # Líneas eliminadas
    imports_fixed: int
    generated_at: datetime


class BlackWidowAgent:
    """
    Black Widow: la cirujana del código.
    Opera sobre el GuardrailReport de Hulk y aplica las correcciones necesarias.
    Widow NO genera código nuevo — solo limpia y reorganiza.
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        file_tools: FileTools,
        shell_tools: ShellTools,
        project_root: Path,
    ): ...

    async def run(self, mission: Mission) -> Mission:
        """
        1. Leer missions/{id}/hulk_report.yaml.
        2. Por cada violación LINE_LIMIT → llamar _split_file().
        3. Por cada violación UNUSED_IMPORT → llamar _fix_imports().
        4. Por cada violación DEAD_CODE → llamar _remove_dead_code().
        5. Por cada violación FORBIDDEN_PATTERN → llamar _replace_forbidden().
        6. Generar WidowReport → guardar en missions/{id}/widow_report.yaml.
        7. Actualizar MAP.yaml con nuevos FileEntry si hubo splits.
        8. Actualizar StateLog y retornar misión.
        """

    async def _split_file(self, file_path: str) -> list[str]:
        """
        Fragmenta un archivo > 300L en sub-módulos coherentes.
        Algoritmo:
        1. Leer el archivo.
        2. Llamar al LLM con el contenido y la instrucción de dividir en módulos
           de responsabilidad única, cada uno ≤ 280L (margen de seguridad).
        3. Guardar cada sub-módulo como archivo nuevo via file_tools.write_file().
        4. Reemplazar el archivo original con imports a los sub-módulos.
        5. Retornar lista de rutas de archivos creados.
        """

    async def _fix_imports(self, file_path: str) -> int:
        """
        Ejecuta: ruff check {file_path} --select F401 --fix
        via shell_tools.run_command().
        Retorna número de imports eliminados.
        """

    async def _remove_dead_code(self, file_path: str) -> int:
        """
        Ejecuta: ruff check {file_path} --select F811,F841 --fix
        Retorna número de líneas eliminadas.
        """

    async def _replace_forbidden(self, file_path: str, violation: GuardrailViolation) -> None:
        """
        Reemplaza patrones prohibidos (open(), os.system...) con los equivalentes
        seguros (file_tools, shell_tools). Usa el LLM para el reemplazo contextual.
        """
```

**Restricciones**:
- `_split_file` usa el LLM para decidir los límites de separación — no dividir mecánicamente por líneas.
- Después de cada modificación, re-ejecutar `file_tools.count_lines()` para verificar el resultado.
- **Este archivo NO debe superar 220 líneas.** Si crece, extraer `_split_file` a `tools/code_splitter.py`.
- Widow jamás elimina tests existentes — si un test referencia código eliminado, documentarlo en `WidowReport`.

---

### TESTS REQUERIDOS: `tests/agents/test_black_widow.py`

```python
# Test 1: run() procesa todas las violaciones del GuardrailReport
async def test_run_processes_all_violations(): ...

# Test 2: _split_file divide en sub-módulos ≤ 280L
async def test_split_file_produces_files_under_limit(): ...

# Test 3: _fix_imports usa ruff --fix (shell_tools mock)
async def test_fix_imports_uses_ruff(): ...

# Test 4: WidowReport guardado en missions/{id}/widow_report.yaml
async def test_widow_report_saved(): ...

# Test 5: MAP.yaml actualizado si hubo splits
async def test_map_updated_after_split(): ...

# Test 6: Widow NO elimina archivos de test
async def test_does_not_delete_test_files(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `agents/black_widow.py` < 220 líneas
- [ ] `_split_file` usa LLM para división semántica (no mecánica)
- [ ] `_fix_imports` y `_remove_dead_code` via `ruff --fix` con `shell_tools`
- [ ] `WidowReport` guardado en `missions/{id}/`
- [ ] MAP.yaml actualizado tras splits
- [ ] Tests de Widow no eliminados
- [ ] 6 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | Todo I/O via `file_tools` — sin `open()` directo |
| **Hulk** | Después de split, verificar que cada sub-módulo pase Hulk |
| **Widow** | Widow no modifica tests — solo código de producción |
