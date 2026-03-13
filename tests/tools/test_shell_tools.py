"""tests/tools/test_shell_tools.py — Suite de seguridad para shell_tools.

Valida que:
- Comandos fuera de ALLOWED_COMMANDS son bloqueados.
- run_command ejecuta correctamente comandos permitidos.
- ShellTimeoutError se lanza cuando el proceso supera el timeout.
- Lista vacía lanza ValueError.
"""

from __future__ import annotations

import pytest

from tools.shell_tools import (
    ALLOWED_COMMANDS,
    CommandNotAllowedError,
    ShellTimeoutError,
    run_command,
)


# ── Lista blanca: comandos bloqueados ────────────────────────────────────────


@pytest.mark.parametrize(
    "forbidden",
    ["rm", "curl", "sudo", "bash", "sh", "wget", "nc", "chmod", "kill", "dd"],
)
async def test_forbidden_command_raises_not_allowed(forbidden: str) -> None:
    with pytest.raises(CommandNotAllowedError) as exc_info:
        await run_command([forbidden, "--help"])
    assert exc_info.value.command == forbidden


# ── Lista blanca: comandos permitidos ────────────────────────────────────────


async def test_allowed_command_echo_runs_successfully() -> None:
    returncode, stdout, stderr = await run_command(["echo", "hello avengers"])
    assert returncode == 0
    assert "hello avengers" in stdout


async def test_allowed_commands_set_contains_expected_tools() -> None:
    expected = {"python", "pytest", "ruff", "mypy", "git"}
    assert expected.issubset(ALLOWED_COMMANDS)


# ── Cmd vacío ─────────────────────────────────────────────────────────────────


async def test_empty_command_raises_value_error() -> None:
    with pytest.raises(ValueError):
        await run_command([])


# ── Timeout ──────────────────────────────────────────────────────────────────


async def test_timeout_raises_shell_timeout_error() -> None:
    """python3 -c 'import time; time.sleep(10)' debe expirar en 0.1 s."""
    with pytest.raises(ShellTimeoutError):
        await run_command(
            ["python3", "-c", "import time; time.sleep(10)"],
            timeout=0.1,
        )


# ── Stderr y returncode ───────────────────────────────────────────────────────


async def test_failed_command_returns_nonzero_returncode() -> None:
    returncode, _stdout, stderr = await run_command(
        ["python3", "-c", "raise SystemExit(42)"]
    )
    assert returncode == 42


async def test_command_not_allowed_error_message_lists_allowed() -> None:
    with pytest.raises(CommandNotAllowedError) as exc_info:
        await run_command(["curl", "http://example.com"])
    assert "curl" in str(exc_info.value)
    assert "Permitidos" in str(exc_info.value)
