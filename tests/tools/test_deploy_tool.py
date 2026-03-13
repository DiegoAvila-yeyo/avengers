"""tests/tools/test_deploy_tool.py — Tests unitarios para DeployTool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tools.deploy_tool import DeployResult, DeployTarget, DeployTool


def _make_settings(deploy_url: str = "https://avengers.example.com") -> MagicMock:
    settings = MagicMock()
    settings.railway_token = None
    settings.vercel_token = None
    settings.deploy_url = deploy_url
    return settings


@pytest.mark.asyncio
async def test_deploy_railway_executes_correct_command() -> None:
    """deploy() Railway ejecuta ['railway', 'up', '--service', 'avengers-api']."""
    settings = _make_settings()
    tool = DeployTool(settings=settings)

    with patch("tools.deploy_tool.run_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "Deployed", "")
        result: DeployResult = await tool.deploy(DeployTarget.RAILWAY, mission_id="m-001")

    mock_run.assert_awaited_once_with(
        ["railway", "up", "--service", "avengers-api"], timeout=240.0
    )
    assert result.success is True
    assert result.target == DeployTarget.RAILWAY
    assert result.deploy_url == "https://avengers.example.com"


@pytest.mark.asyncio
async def test_health_check_passes_on_200() -> None:
    """health_check retorna True cuando el endpoint responde 200."""
    settings = _make_settings()
    tool = DeployTool(settings=settings)

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await tool.health_check("https://avengers.example.com", retries=3)

    assert result is True


@pytest.mark.asyncio
async def test_health_check_fails_after_retries() -> None:
    """health_check retorna False cuando todos los reintentos fallan."""
    settings = _make_settings()
    tool = DeployTool(settings=settings)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await tool.health_check("https://avengers.example.com", retries=3)

    assert result is False
