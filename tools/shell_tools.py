"""tools/shell_tools.py — Ejecución segura de subprocesos con lista blanca.

Solo los comandos en ALLOWED_COMMANDS pueden ejecutarse. Cualquier intento
de ejecutar un binario fuera de esa lista lanza CommandNotAllowedError.
"""

from __future__ import annotations

import asyncio

from core.exceptions import AvengersBaseError

# Lista blanca estricta — Iron-Coder solo necesita estas herramientas.
ALLOWED_COMMANDS: frozenset[str] = frozenset(
    {"python", "python3", "pytest", "ruff", "mypy", "git", "pip", "uv", "echo"}
)


class CommandNotAllowedError(AvengersBaseError):
    """Se lanza cuando el comando solicitado no está en ALLOWED_COMMANDS."""

    def __init__(self, command: str) -> None:
        self.command = command
        super().__init__(
            f"Comando '{command}' bloqueado por lista blanca. "
            f"Permitidos: {sorted(ALLOWED_COMMANDS)}"
        )


class ShellTimeoutError(AvengersBaseError):
    """Se lanza cuando el subproceso supera el timeout configurado."""

    def __init__(self, command: str, timeout: float) -> None:
        super().__init__(f"Comando '{command}' excedió el timeout de {timeout}s.")


async def run_command(
    cmd: list[str],
    timeout: float = 30.0,
) -> tuple[int, str, str]:
    """Ejecuta *cmd* como subproceso asíncrono con timeout estricto.

    Args:
        cmd:     Lista [binario, *args]. El binario debe estar en ALLOWED_COMMANDS.
        timeout: Segundos máximos de ejecución (default: 30 s).

    Returns:
        Tupla (returncode, stdout, stderr).

    Raises:
        CommandNotAllowedError: Si el binario no está en la lista blanca.
        ShellTimeoutError:      Si el proceso supera *timeout* segundos.
        ValueError:             Si *cmd* está vacío.
    """
    if not cmd:
        raise ValueError("cmd no puede estar vacío.")

    binary = cmd[0]
    if binary not in ALLOWED_COMMANDS:
        raise CommandNotAllowedError(binary)

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise ShellTimeoutError(binary, timeout)

    return (
        proc.returncode if proc.returncode is not None else -1,
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace"),
    )
