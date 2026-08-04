"""Inspect and safely operate systemd services."""
from __future__ import annotations

import argparse
import re
import shlex
import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command
from forgetools.linux.privilege import inspect_command

TOOL = "linux.services"
READ_ACTIONS = {"list", "status", "is-active"}
MUTATING_ACTIONS = {"start", "stop", "restart", "enable", "disable", "mask", "unmask"}
ACTIONS = tuple(sorted(READ_ACTIONS | MUTATING_ACTIONS))
UNIT_RE = re.compile(r"^[A-Za-z0-9_.@:-]+$")


def run(*, action: str = "list", unit: str = "", execute: bool = False,
        confirm: bool = False, cwd: str | None = None) -> ForgeResult:
    with Timer() as timer:
        if action not in ACTIONS:
            return ForgeResult.failure(TOOL, [f"Unknown action: {action}"], timer.elapsed_ms,
                                       suggestion=f"Use one of: {', '.join(ACTIONS)}")
        if action not in {"list"} and not unit:
            return ForgeResult.failure(TOOL, [f"unit is required for action={action}"], timer.elapsed_ms)
        if unit and not UNIT_RE.fullmatch(unit):
            return ForgeResult.failure(TOOL, [f"Invalid systemd unit: {unit}"], timer.elapsed_ms)
        if not shutil.which("systemctl"):
            return ForgeResult.failure(TOOL, ["systemctl not found"], timer.elapsed_ms,
                                       suggestion="This tool requires a systemd host")
        command = _command(action, unit)
        privilege = inspect_command(shlex.join(command), cwd=cwd) if action in MUTATING_ACTIONS else None
        if action in MUTATING_ACTIONS and not execute:
            return ForgeResult.success(TOOL, {"action": action, "unit": unit, "command": command,
                                              "privilege_preflight": privilege,
                                              "preview": True, "executed": False,
                                              "requires_confirmation": True}, timer.elapsed_ms)
        if action in MUTATING_ACTIONS and not confirm:
            return ForgeResult.failure(TOOL, ["Explicit confirmation is required for service mutations"],
                                       timer.elapsed_ms,
                                       suggestion="Call again with execute=true and confirm=true after reviewing the preview")
        if action in MUTATING_ACTIONS and privilege and not privilege["can_run_with_sudo"]:
            return ForgeResult.failure(
                TOOL,
                [f"Privilege preflight rejected service mutation: {privilege['recommendation']}"],
                timer.elapsed_ms,
                suggestion="Run linux_privilege for the exact command, configure non-interactive sudo, or execute as root",
            )
        rc, stdout, stderr = run_command(command, cwd=cwd, timeout=60)
        if action == "is-active" and rc in (0, 3):
            return ForgeResult.success(TOOL, {"action": action, "unit": unit, "active": rc == 0,
                                              "state": stdout.strip() or stderr.strip()}, timer.elapsed_ms)
        if rc != 0:
            return ForgeResult.failure(TOOL, [stderr.strip() or f"systemctl exited with code {rc}"], timer.elapsed_ms)
        return ForgeResult.success(TOOL, {"action": action, "unit": unit, "command": command,
                                          "output": stdout.strip(), "executed": action in MUTATING_ACTIONS,
                                          "preview": False}, timer.elapsed_ms)


def _command(action: str, unit: str) -> list[str]:
    if action == "list":
        return ["systemctl", "list-units", "--type=service", "--all", "--no-legend", "--no-pager"]
    if action == "status":
        return ["systemctl", "show", unit, "--no-pager", "--property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID"]
    if action == "is-active":
        return ["systemctl", "is-active", unit]
    return ["systemctl", action, unit]


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--action", default="list", choices=ACTIONS)
    parser.add_argument("--unit", default="")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "Inspect or safely operate systemd services", run, _add_args)
