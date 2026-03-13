"""tools/deploy_tool.py — Helper async para deploys via CLI de Railway y Vercel."""

from __future__ import annotations

import asyncio
import time
from enum import Enum

import httpx
from pydantic import BaseModel

from core.settings import Settings
from tools.shell_tools import run_command


class DeployTarget(str, Enum):  # noqa: UP042
    VERCEL = "vercel"
    RAILWAY = "railway"
    LOCAL = "local"


class DeployResult(BaseModel):
    target: DeployTarget
    success: bool
    deploy_url: str | None
    duration_seconds: float
    error_message: str | None = None


class DeployTool:
    """Permite que Nick Fury dispare deploys via CLI de Vercel/Railway."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def deploy(self, target: DeployTarget, mission_id: str) -> DeployResult:
        """Ejecuta el deploy via CLI y retorna un DeployResult."""
        start = time.monotonic()
        if target == DeployTarget.LOCAL:
            return DeployResult(
                target=target,
                success=True,
                deploy_url="http://localhost:8000",
                duration_seconds=time.monotonic() - start,
            )
        try:
            if target == DeployTarget.RAILWAY:
                cmd = ["railway", "up", "--service", "avengers-api"]
            else:
                t = self._settings.vercel_token
                raw = t.get_secret_value() if t else ""
                cmd = ["vercel", "--prod", "--token", raw]
            returncode, _out, stderr = await run_command(cmd, timeout=240.0)
            success = returncode == 0
            return DeployResult(
                target=target,
                success=success,
                deploy_url=self._settings.deploy_url if success else None,
                duration_seconds=time.monotonic() - start,
                error_message=stderr.strip() if not success else None,
            )
        except Exception as exc:
            return DeployResult(
                target=target,
                success=False,
                deploy_url=None,
                duration_seconds=time.monotonic() - start,
                error_message=str(exc),
            )

    async def health_check(self, url: str, retries: int = 5) -> bool:
        """GET {url}/health con backoff exponencial. True si 200, False si agota reintentos."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(retries):
                try:
                    if (await client.get(f"{url}/health")).status_code == 200:
                        return True
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(2**attempt)
        return False
