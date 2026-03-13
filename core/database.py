"""core/database.py — Ciclo de vida de la conexión MongoDB (async).

ADR-001: usa motor (async driver) para no bloquear el event loop de FastAPI.
AMD-05 PERSISTENCIA: expone `db_manager` (singleton) y `get_database()`.

Uso en FastAPI lifespan:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await db_manager.connect()
        yield
        await db_manager.close()
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.settings import settings

logger = logging.getLogger(__name__)

_DB_NAME_FALLBACK = "avengers"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_db_name(url: str) -> str:
    """Extrae el nombre de BD del URL; usa fallback si el path está vacío."""
    name = urlparse(url).path.lstrip("/")
    return name if name else _DB_NAME_FALLBACK


# ── Manager ───────────────────────────────────────────────────────────────────


class DatabaseManager:
    """Gestiona el ciclo de vida del AsyncIOMotorClient.

    Protocolo Widow: el cliente se cierra explícitamente en close()
    para evitar conexiones abiertas al finalizar la aplicación.
    """

    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
        self._db_name: str = _extract_db_name(settings.database_url)

    async def connect(self) -> None:
        """Abre el pool de conexiones a MongoDB. Idempotente."""
        if self._client is not None:
            return
        self._client = AsyncIOMotorClient(settings.database_url)
        logger.info("MongoDB conectado → base de datos: %s", self._db_name)

    async def close(self) -> None:
        """Cierra el pool de conexiones. Protocolo Widow: sin fugas de recursos."""
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("MongoDB cliente cerrado.")

    def get_database(self) -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
        """Devuelve la base de datos activa.

        Raises:
            RuntimeError: si connect() no fue llamado antes.
        """
        if self._client is None:
            raise RuntimeError(
                "DatabaseManager no está conectado. "
                "Llama `await db_manager.connect()` al arrancar la app."
            )
        return self._client[self._db_name]


# Singleton — un único cliente compartido por toda la aplicación.
db_manager = DatabaseManager()
