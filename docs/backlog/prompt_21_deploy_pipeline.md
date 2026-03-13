# Prompt #21 — Pipeline CI/CD: GitHub Actions → Deploy Automático

**Fase**: 5 — Ciclo de Cierre
**Agente objetivo**: Core
**Archivo(s) a crear**:
- `.github/workflows/deploy.yml` — Pipeline CI/CD completo
- `tools/deploy_tool.py` — Helper async para trigger de deploy via API
**Dependencias previas**: Prompt #20 (QAReport aprobado), Prompt #01 (Settings)
**Checkpoint humano**: **[👤 HUMANO]** — Confirmar destino de deploy (Vercel/Railway) y secrets configurados

---

## 📋 Prompt Completo

---

Actúa como un Senior DevOps Engineer especializado en CI/CD con GitHub Actions,
trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → Fase 5 del Bucle Infinito (Deploy).
3. Lee `pyproject.toml` → dependencias y versión de Python.
4. Lee `core/settings.py` → variables de entorno necesarias.

---

### TAREA: Crear el pipeline CI/CD

#### ARCHIVO 1: `.github/workflows/deploy.yml`

El workflow debe tener **dos jobs**:

**Job 1: `quality-gate`** (se ejecuta en todo PR y push a main)
```yaml
# Pasos:
# 1. checkout
# 2. Setup Python 3.12
# 3. Install deps: pip install -e ".[dev]"
# 4. ruff check . (falla si hay violaciones)
# 5. mypy . (falla si hay errores de tipos)
# 6. pytest tests/ --cov=. --cov-fail-under=80 (falla si cobertura < 80%)
```

**Job 2: `deploy`** (se ejecuta solo en push a `main`, después de `quality-gate`)
```yaml
# Estrategia: deploy a Vercel (frontend) + Railway (backend)
# Pasos:
# 1. Deploy backend a Railway via CLI: railway up --service avengers-api
# 2. Deploy frontend a Vercel via CLI: vercel --prod --token $VERCEL_TOKEN
# 3. Health check: curl {DEPLOY_URL}/health → esperar 200
# 4. Si health check falla → rollback automático + notificación
#
# Secrets necesarios (documentar):
#   RAILWAY_TOKEN, VERCEL_TOKEN, DEPLOY_URL
```

**Restricciones del YAML**:
- Usar `actions/cache` para pip deps (key: `pyproject.toml` hash).
- Timeouts: `quality-gate` max 10 min, `deploy` max 5 min.
- El job `deploy` tiene `concurrency: group: production, cancel-in-progress: false`.

---

#### ARCHIVO 2: `tools/deploy_tool.py`

```python
class DeployTarget(str, Enum):
    VERCEL = "vercel"
    RAILWAY = "railway"
    LOCAL = "local"    # Para testing

class DeployResult(BaseModel):
    target: DeployTarget
    success: bool
    deploy_url: str | None
    duration_seconds: float
    error_message: str | None = None

class DeployTool:
    """
    Permite que Nick Fury dispare deploys programáticamente
    (complemento al GitHub Actions workflow).
    Usa shell_tools para ejecutar CLI de Vercel/Railway.
    """

    def __init__(self, shell_tools: ShellTools, settings: Settings): ...

    async def deploy(self, target: DeployTarget, mission_id: str) -> DeployResult:
        """
        Ejecuta el deploy via CLI.
        Railway: shell_tools.run_command(["railway", "up", ...])
        Vercel:  shell_tools.run_command(["vercel", "--prod", ...])
        Retorna DeployResult con la URL del deploy.
        """

    async def health_check(self, url: str, retries: int = 5) -> bool:
        """
        GET {url}/health → esperar status 200.
        Reintenta con backoff (1s, 2s, 4s...).
        Retorna True si ok, False si falla tras todos los reintentos.
        """
```

**Restricciones**:
- `deploy_tool.py` NO debe superar **80 líneas**.
- Nunca hardcodear tokens — siempre desde `Settings`.
- El `health_check` usa `httpx.AsyncClient` — no subprocess curl.

---

### TESTS REQUERIDOS: `tests/tools/test_deploy_tool.py`

```python
# Test 1: deploy() Railway ejecuta el comando correcto via shell_tools
async def test_deploy_railway_executes_correct_command(): ...

# Test 2: health_check retorna True en 200
async def test_health_check_passes_on_200(): ...

# Test 3: health_check reintenta y retorna False en timeout
async def test_health_check_fails_after_retries(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `.github/workflows/deploy.yml` con 2 jobs (quality-gate + deploy)
- [ ] `cache` de pip configurado
- [ ] `concurrency` en job deploy (no deploy en paralelo)
- [ ] `tools/deploy_tool.py` < 80 líneas
- [ ] `health_check` con backoff exponencial
- [ ] 3 tests passing
- [ ] Secrets documentados en comentarios del YAML

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Hulk** | `deploy_tool.py` < 80L |
| **Widow** | Cero steps duplicados en el YAML |
| **Seguridad** | Tokens SIEMPRE desde GitHub Secrets, nunca en el YAML |
