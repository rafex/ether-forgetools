"""Manage named Podman service destinations, including SSH connections."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "podman.connection"
_ACTIONS = ("list", "inspect", "add", "default", "remove")
_MUTATING = {"add", "default", "remove"}


def run(
    *,
    action: str = "list",
    name: str = "",
    destination: str = "",
    identity: str = "",
    socket_path: str = "",
    port: int | None = None,
    make_default: bool = False,
    execute: bool = False,
    confirm: bool = False,
    cwd: str | None = None,
) -> ForgeResult:
    """Preview or execute Podman system connection operations safely."""
    with Timer() as timer:
        if action not in _ACTIONS:
            return ForgeResult.failure(TOOL, [f"Invalid action: {action}"], timer.elapsed_ms)
        if action in {"inspect", "default", "remove"} and not name:
            return ForgeResult.failure(TOOL, [f"name is required for action={action}"], timer.elapsed_ms)
        if action == "add" and (not name or not destination):
            return ForgeResult.failure(TOOL, ["name and destination are required for action=add"], timer.elapsed_ms)

        cmd = ["podman", "system", "connection", action]
        if action == "add":
            if make_default:
                cmd.append("--default")
            if identity:
                cmd.extend(["--identity", identity])
            if socket_path:
                cmd.extend(["--socket-path", socket_path])
            if port is not None:
                cmd.extend(["--port", str(port)])
            cmd.extend([name, destination])
        elif action == "list":
            cmd.extend(["--format", "json"])
        else:
            cmd.append(name)

        if action in _MUTATING and not execute:
            return ForgeResult.success(
                TOOL,
                {"action": action, "command": cmd, "preview": True, "executed": False, "requires_confirmation": True},
                timer.elapsed_ms,
            )
        if action in _MUTATING and not confirm:
            return ForgeResult.failure(
                TOOL,
                ["Explicit confirmation is required for this connection mutation"],
                timer.elapsed_ms,
                "Review the preview, then call with execute=true and confirm=true",
            )
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=60)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["podman not found"], timer.elapsed_ms, "Install Podman and configure the SSH service destination")
        except Exception as exc:
            return ForgeResult.failure(TOOL, [str(exc)], timer.elapsed_ms)
        if rc != 0:
            return ForgeResult.failure(TOOL, [stderr.strip() or stdout.strip() or f"podman connection {action} failed"], timer.elapsed_ms, "Verify the destination, SSH identity, and remote rootless Podman socket")
        return ForgeResult.success(TOOL, {"action": action, "command": cmd, "stdout": stdout, "stderr": stderr}, timer.elapsed_ms)


def _args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--action", choices=_ACTIONS, default="list")
    parser.add_argument("--name", default="", help="Named Podman connection")
    parser.add_argument("--destination", default="", help="SSH host, ssh:// URI, unix:// URI, or tcp:// URI")
    parser.add_argument("--identity", default="", help="SSH private key path")
    parser.add_argument("--socket-path", default="", help="Remote Podman API socket path")
    parser.add_argument("--port", type=int, default=None, help="SSH port")
    parser.add_argument("--make-default", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Execute a mutating action; preview is the default")
    parser.add_argument("--confirm", action="store_true", help="Confirm the reviewed mutating command")


if __name__ == "__main__":
    make_cli(TOOL, "Preview or execute Podman local and SSH service connection operations", run, _args)
