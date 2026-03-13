# Prompt #02 — Capa de Datos: MongoDB async con motor

**Fase**: 1 — Sistema Nervioso Central
**Agente objetivo**: Core
**Archivo(s) a crear**:
- `core/database.py` — Conexión y cliente MongoDB async (motor)
- `core/repositories.py` — Repositorio de misiones y checkpoints
**Dependencias previas**: Prompt #01 (Settings, constantes)
**Checkpoint humano**: No

### 🔒 Enmienda AMD-05 Persistencia Estricta
Este módulo es el **único** responsable de la persistencia. Todo agente que necesite
guardar estado lo hace a través del repositorio definido aquí. La persistencia no es
opcional ni diferida — cada cambio de estado se escribe a MongoDB inmediatamente.

---

## 📋 Prompt Completo

---

Actúa como un Senior Developer Python especializado en bases de datos async y patrones
de repositorio, trabajando en el proyecto AVENGERS.

**CONTEXTO OBLIGATORIO — lee antes de escribir una sola línea:**
1. Lee `.github/copilot-instructions.md` → convenciones, Protocolo Hulk y Widow.
2. Lee `ARCHITECTURE.md` → decisión ADR-001 (motor async).
3. Lee `core/settings.py` → `get_settings()`, nombres de colecciones.
4. Lee `core/constants.py` → `COL_MISSIONS`, `COL_CHECKPOINTS`.

---

### TAREA: Crear la capa de datos async

#### ARCHIVO 1: `core/database.py`

```python
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from functools import lru_cache
from core.settings import get_settings

_client: AsyncIOMotorClient | None = None

async def connect_db() -> None:
    """Inicializa la conexión MongoDB. Llamar al startup de la app."""
    global _client
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.database_url)
    # Verificar conexión real con ping
    await _client.admin.command("ping")

async def disconnect_db() -> None:
    """Cierra la conexión MongoDB. Llamar al shutdown de la app."""
    global _client
    if _client:
        _client.close()
        _client = None

def get_database() -> AsyncIOMotorDatabase:
    """
    Retorna la base de datos activa.
    Lanza RuntimeError si connect_db() no fue llamado.
    """
    if _client is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _client[get_settings().db_name]
```

**Restricciones**:
- No usar `@lru_cache` en `get_database()` — el cliente se gestiona con variable global.
- El `_client` global se testea con mocks; no crear conexión real en tests.
- **Este archivo NO debe superar 60 líneas.**

---

#### ARCHIVO 2: `core/repositories.py`

```python
from core.models import Mission, MissionStatus
from core.constants import COL_MISSIONS, COL_CHECKPOINTS
from core.exceptions import StatePersistenceError

class MissionRepository:
    """
    Repositorio async para misiones. Única capa que toca MongoDB directamente.
    Todos los métodos son async. Nunca bloquear el event loop.
    """

    def __init__(self, db: AsyncIOMotorDatabase): ...

    async def save_mission(self, mission: Mission) -> Mission:
        """
        Upsert de la misión completa (usa mission_id como filtro).
        [AMD-05 PERSISTENCIA ESTRICTA] — toda mutación de Mission llama este método.
        Lanza StatePersistenceError si el write falla.
        Retorna la misión guardada.
        """

    async def get_mission(self, mission_id: str) -> Mission | None:
        """Busca por mission_id. Retorna None si no existe."""

    async def list_missions(
        self,
        status: MissionStatus | None = None,
        limit: int = 50,
    ) -> list[Mission]:
        """Lista misiones, opcionalmente filtradas por status."""

    async def delete_mission(self, mission_id: str) -> bool:
        """Elimina una misión. Retorna True si fue eliminada, False si no existía."""


class CheckpointRepository:
    """Repositorio async para CheckpointRecords."""

    def __init__(self, db: AsyncIOMotorDatabase): ...

    async def save_checkpoint(self, checkpoint: "CheckpointRecord") -> "CheckpointRecord":
        """Upsert de un checkpoint por checkpoint_id."""

    async def get_checkpoint(self, checkpoint_id: str) -> "CheckpointRecord | None": ...

    async def list_pending(self, mission_id: str) -> list["CheckpointRecord"]:
        """Retorna checkpoints sin resolver para una misión."""
```

**Restricciones**:
- Serialización: usar `mission.model_dump(mode="json")` para MongoDB (no `dict()`).
- Deserialización: usar `Mission.model_validate(doc)` para reconstruir desde Mongo.
- El campo `_id` de MongoDB NO se expone fuera del repositorio; usar `mission_id` como key.
- **`core/repositories.py` NO debe superar 150 líneas.**

---

### TESTS REQUERIDOS: `tests/core/test_repositories.py`

```python
# Usar mongomock-motor o motor con MongoDB en memoria para tests

# Test 1: save_mission → upsert correcto, recuperable con get_mission
async def test_save_and_get_mission(): ...

# Test 2: save_mission con error de escritura → StatePersistenceError
async def test_save_raises_persistence_error_on_failure(): ...

# Test 3: get_mission con ID inexistente → None
async def test_get_mission_returns_none_for_unknown_id(): ...

# Test 4: list_missions filtra por status correctamente
async def test_list_missions_filters_by_status(): ...

# Test 5: save_mission serializa/deserializa el modelo completo sin pérdida
async def test_mission_round_trip_serialization(): ...

# Test 6: connect_db falla si URL incorrecta → RuntimeError manejable
async def test_connect_db_fails_gracefully(): ...
```

### CHECKLIST DE ENTREGA

- [ ] `core/database.py` < 60 líneas
- [ ] `core/repositories.py` < 150 líneas
- [ ] `StatePersistenceError` lanzada en fallo de write
- [ ] Serialización via `model_dump(mode="json")` — no `dict()`
- [ ] `_id` de MongoDB encapsulado, nunca expuesto
- [ ] 6 tests passing con mock de MongoDB
- [ ] `ruff check` y `mypy` sin errores

### ⚠️ PROTOCOLOS ACTIVOS
| Protocolo | Acción |
|---|---|
| **Persistencia Estricta** | `save_mission()` en cada mutación — obligatorio |
| **Hulk** (> 300L) | DETENTE, modulariza |
| **Widow** | Ningún método sin usar |
