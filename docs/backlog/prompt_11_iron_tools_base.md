# Prompt #11 — Iron-Coder Tools: Herramientas Atómicas con Root Jail

**Fase**: 3 — La Fábrica
**Agente objetivo**: Iron-Coder
**Archivo(s) a crear**:
- `tools/file_tools.py` — Operaciones de lectura/escritura de archivos
- `tools/shell_tools.py` — Ejecución de comandos de shell
**Dependencias previas**: Prompt #04 (excepciones, `RootJailViolationError`)
**Checkpoint humano**: No

### 🔒 Cláusula de Seguridad ROOT JAIL (v0.3.0) — OBLIGATORIA
> Esta cláusula se aplica a TODOS los archivos de `tools/` sin excepción.

**Cualquier operación de escritura o lectura de archivos DEBE estar restringida al
directorio raíz del proyecto (`PROJECT_ROOT`). El sistema debe lanzar
`RootJailViolationError` inmediatamente si se detecta cualquier intento de acceder
a rutas externas al proyecto (path traversal, rutas absolutas fuera de `PROJECT_ROOT`,
symlinks que apuntan fuera, etc.).**

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en seguridad de sistemas de archivos
y herramientas para agentes de IA, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolos Hulk y Widow.
2. Lee `core/exceptions.py` → `RootJailViolationError`.
3. Lee `core/models.py` → `AgentRole`.

---

### TAREA: Crear las herramientas atómicas de Iron-Coder

#### ARCHIVO 1: `tools/file_tools.py`

```python
# PROJECT_ROOT se obtiene de settings (pydantic-settings)
# Nunca hardcodear rutas absolutas.

def resolve_safe_path(relative_path: str | Path, project_root: Path) -> Path:
    """
    Convierte una ruta relativa en absoluta y verifica que esté dentro de project_root.

    Algoritmo de seguridad:
    1. Resolver a absoluta: `(project_root / relative_path).resolve()`
    2. Verificar que la ruta resuelta empiece con `project_root.resolve()`.
    3. Si no → lanzar RootJailViolationError con detalle de la ruta bloqueada.
    4. Si sí → retornar la ruta absoluta segura.

    Protege contra: "../../../etc/passwd", symlinks maliciosos, rutas absolutas.
    """

async def read_file(relative_path: str, project_root: Path) -> str:
    """Lee un archivo de texto. Siempre pasa por resolve_safe_path."""

async def write_file(relative_path: str, content: str, project_root: Path) -> Path:
    """
    Escribe contenido en un archivo.
    - Siempre pasa por resolve_safe_path.
    - Crea directorios intermedios si no existen (mkdir parents=True).
    - NO sobreescribe archivos existentes sin el flag overwrite=True explícito.
    Retorna la ruta absoluta del archivo escrito.
    """

async def list_files(relative_dir: str, pattern: str, project_root: Path) -> list[str]:
    """
    Lista archivos en un directorio usando glob.
    Siempre pasa por resolve_safe_path antes de hacer el glob.
    Retorna rutas RELATIVAS al project_root (no absolutas).
    """

async def count_lines(relative_path: str, project_root: Path) -> int:
    """Cuenta líneas de un archivo. Usado por Hulk para auditoría."""
```

#### ARCHIVO 2: `tools/shell_tools.py`

```python
# Lista blanca de comandos permitidos — todo lo demás es rechazado
ALLOWED_COMMANDS: frozenset[str] = frozenset({
    "python", "pip", "pytest", "ruff", "mypy", "git", "cat", "ls", "find"
})

async def run_command(
    cmd: list[str],
    cwd: str,
    project_root: Path,
    timeout_seconds: int = 30,
) -> tuple[int, str, str]:
    """
    Ejecuta un comando de shell de forma segura.

    Seguridad:
    1. `cmd[0]` (el ejecutable) debe estar en ALLOWED_COMMANDS. Si no → lanzar
       `RootJailViolationError` con mensaje "Comando no permitido: {cmd[0]}".
    2. `cwd` debe pasar por `resolve_safe_path(cwd, project_root)`.
    3. El proceso NO hereda variables de entorno del padre (env mínimo).
    4. Timeout obligatorio — si supera `timeout_seconds` → terminar proceso y
       retornar código de salida 124.

    Retorna: (return_code, stdout, stderr)
    """
```

**Restricciones**:
- `resolve_safe_path` es la función más crítica del sistema. Debe ser testada exhaustivamente.
- Usar `asyncio.create_subprocess_exec` (NO `subprocess.run` ni `os.system`).
- **`tools/file_tools.py` NO debe superar 100 líneas.**
- **`tools/shell_tools.py` NO debe superar 80 líneas.**

---

### TESTS REQUERIDOS: `tests/tools/test_file_tools.py` y `tests/tools/test_shell_tools.py`

```python
# file_tools tests
def test_resolve_safe_path_allows_valid_relative():      ...  # "src/main.py" → ok
def test_resolve_safe_path_blocks_traversal():           ...  # "../../etc/passwd" → RootJailViolationError
def test_resolve_safe_path_blocks_absolute_outside():    ...  # "/etc/passwd" → RootJailViolationError
async def test_write_file_creates_directories():         ...
async def test_write_file_blocks_overwrite_by_default(): ...
async def test_count_lines_returns_correct_count():      ...

# shell_tools tests
async def test_run_command_allows_pytest():              ...  # ["pytest", "--version"] → ok
async def test_run_command_blocks_rm():                  ...  # ["rm", "-rf", "/"] → RootJailViolationError
async def test_run_command_enforces_cwd_jail():          ...  # cwd fuera del proyecto → error
async def test_run_command_respects_timeout():           ...  # comando largo → return_code 124
```

### CHECKLIST DE ENTREGA

- [ ] `tools/file_tools.py` < 100 líneas
- [ ] `tools/shell_tools.py` < 80 líneas
- [ ] `resolve_safe_path` protege contra path traversal, absolutos y symlinks
- [ ] `ALLOWED_COMMANDS` como `frozenset` (inmutable)
- [ ] Timeout en todos los subprocesos
- [ ] 10 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **ROOT JAIL** | `resolve_safe_path()` en TODA operación de I/O — sin excepciones |
| **Hulk** (> 300L) | DETENTE, modulariza |
| **Widow** | `ALLOWED_COMMANDS` debe incluir solo lo necesario — sin bloat |
