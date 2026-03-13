# Prompt #22 — El Infiltrado: Poster Automático en X y Reddit

**Fase**: 5 — Ciclo de Cierre
**Agente objetivo**: El Infiltrado
**Archivo(s) a crear**:
- `agents/infiltrado.py` — Agente de distribución: genera y publica contenido
**Dependencias previas**: Prompt #07 (XSource, RedditSource — los reutiliza para postear), Prompt #21 (DeployResult con URL)
**Checkpoint humano**: **[👤 HUMANO]** — Aprobar los mensajes de marketing antes de publicar

### ⚠️ Nota de Seguridad
Este agente **nunca publica automáticamente** sin aprobación humana.
El flujo es: generar mensajes → Checkpoint `[👤 HUMANO]` → publicar solo tras aprobación.

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en APIs de redes sociales y
marketing automation, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → Fase 6 del Bucle Infinito (Distribución).
3. Lee `core/blueprint_schema.py` → `BlueprintV1` (qué producto vender).
4. Lee `tools/sources/x_source.py` y `reddit_source.py` → APIs disponibles.
5. Lee `core/checkpoints.py` → `CheckpointManager.trigger()` (aprobación obligatoria).

---

### TAREA: Implementar el agente El Infiltrado

#### ARCHIVO: `agents/infiltrado.py`

```python
class SocialPost(BaseModel):
    platform: str            # "x" | "reddit"
    content: str             # Texto del post (con URL del producto)
    subreddit: str | None    # Solo para Reddit
    thread_title: str | None # Solo para Reddit (título del post)
    approved: bool = False   # Solo se publica si True (aprobación humana)
    published_at: datetime | None = None
    post_url: str | None = None  # URL del post publicado


class InfiltradoAgent:
    """
    El agente de growth. Genera contenido para X y Reddit, espera aprobación
    humana, y luego publica. Recoge engagement como feedback para Thor.
    """

    CONTENT_PROMPT: ClassVar[str] = """
    Eres un Growth Hacker expert en comunidades técnicas.
    Genera posts auténticos (no spammy) para promocionar el producto.
    Reglas:
    - X post: ≤ 280 chars. Incluir URL, 2-3 hashtags relevantes.
    - Reddit: título descriptivo + comentario de valor genuino.
      NUNCA "Check out my product". Aportar valor primero.
    - Tono: developer-to-developer, honesto sobre las limitaciones del producto.
    - Incluir la URL del deploy en cada post.
    Output: JSON con lista de SocialPost.
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        x_source: "XSource",
        reddit_source: "RedditSource",
        checkpoint_manager: "CheckpointManager",
        file_tools: FileTools,
    ): ...

    async def run(self, mission: Mission) -> Mission:
        """
        1. Leer blueprint.yaml y DeployResult (URL del producto).
        2. Llamar _generate_posts(blueprint, deploy_url) → lista de SocialPost.
        3. Guardar posts en missions/{id}/social_posts.yaml (draft, approved=False).
        4. Trigger Checkpoint humano → esperar aprobación.
        5. Tras aprobación → llamar _publish_approved_posts().
        6. Actualizar StateLog y retornar misión.
        """

    async def _generate_posts(
        self, blueprint: BlueprintV1, deploy_url: str
    ) -> list[SocialPost]:
        """
        Genera posts para X (2 variantes) y Reddit (1 post en subreddit relevante).
        Usa LLM con CONTENT_PROMPT + context JIT (product_name, problem_statement, URL).
        """

    async def _publish_approved_posts(self, posts: list[SocialPost], mission: Mission) -> list[SocialPost]:
        """
        Publica solo los posts con approved=True.
        X: POST /2/tweets via x_source._make_request().
        Reddit: submit post via reddit_source API.
        Actualiza post.published_at y post.post_url.
        """
```

**Restricciones**:
- El agente **NO publica** sin `post.approved == True`. Esta verificación es un guard obligatorio.
- Posts guardados en `missions/{id}/social_posts.yaml` via `file_tools` (ROOT JAIL).
- **Este archivo NO debe superar 180 líneas.**

---

### TESTS REQUERIDOS: `tests/agents/test_infiltrado.py`

```python
# Test 1: run() genera posts Y espera checkpoint antes de publicar
async def test_run_generates_then_checkpoints(): ...

# Test 2: _publish_approved_posts NO publica posts con approved=False
async def test_publish_skips_unapproved_posts(): ...

# Test 3: posts guardados en missions/{id}/social_posts.yaml
async def test_posts_saved_as_draft(): ...

# Test 4: X post ≤ 280 chars en contenido generado
def test_x_post_respects_character_limit(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `agents/infiltrado.py` < 180 líneas
- [ ] Guard obligatorio: `approved=True` antes de publicar
- [ ] Checkpoint humano bloqueante antes de cualquier publicación
- [ ] Posts guardados como draft en `missions/{id}/`
- [ ] 4 tests passing
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Checkpoint Humano** | OBLIGATORIO antes de publicar — sin excepción |
| **ROOT JAIL** | `social_posts.yaml` en `missions/{id}/` via `file_tools` |
| **Hulk** | < 180L — si crece, extraer `_generate_posts` a `tools/content_generator.py` |
| **Widow** | Cero código de publicación fuera de `_publish_approved_posts` |
