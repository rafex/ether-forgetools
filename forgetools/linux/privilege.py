"""Preflight command execution and non-interactive sudo authorization."""
from __future__ import annotations

import argparse
import os
import shlex
import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "linux.privilege"
SHELL_TOKENS = {"|", "||", "&", "&&", ";", ">", ">>", "<", "2>", "2>>"}


def inspect_command(command: str, *, cwd: str | None = None) -> dict:
    """Return privilege facts without executing the requested command."""
    tokens = _parse_command(command)
    executable = tokens[0]
    executable_path = shutil.which(executable) if not os.path.isabs(executable) else executable
    running_as_root = hasattr(os, "geteuid") and os.geteuid() == 0
    sudo_path = shutil.which("sudo")
    result = {
        "command": command,
        "argv": tokens,
        "executable": executable,
        "executable_path": executable_path,
        "binary_available": bool(executable_path and os.access(executable_path, os.X_OK)),
        "running_as_root": running_as_root,
        "sudo_available": bool(sudo_path),
        "sudo_non_interactive": False,
        "sudo_policy_allows_command": False,
        "can_run_with_sudo": running_as_root,
        "recommendation": "direct" if running_as_root else "unknown",
    }
    if not result["binary_available"]:
        result["recommendation"] = "binary-not-found"
        return result
    if running_as_root or not sudo_path:
        if not running_as_root:
            result["recommendation"] = "direct-or-permission-error"
        return result

    validate_rc, validate_out, validate_err = run_command([sudo_path, "-n", "-v"], cwd=cwd, timeout=5)
    list_rc, list_out, list_err = run_command(
        [sudo_path, "-n", "-l", "--", executable_path, *tokens[1:]], cwd=cwd, timeout=5
    )
    result.update({
        "sudo_non_interactive": validate_rc == 0,
        "sudo_policy_allows_command": list_rc == 0,
        "sudo_validation_output": (validate_out or validate_err).strip()[:1000],
        "sudo_policy_output": (list_out or list_err).strip()[:2000],
        "can_run_with_sudo": list_rc == 0 and validate_rc == 0,
    })
    if result["can_run_with_sudo"]:
        result["recommendation"] = "sudo-non-interactive"
    elif list_rc == 0:
        result["recommendation"] = "sudo-password-or-interactive-required"
    elif validate_rc != 0:
        result["recommendation"] = "sudo-not-authorized-or-password-required"
    else:
        result["recommendation"] = "sudo-policy-does-not-allow-command"
    return result


def run(*, command: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as timer:
        try:
            data = inspect_command(command, cwd=cwd)
        except ValueError as exc:
            return ForgeResult.failure(TOOL, [str(exc)], timer.elapsed_ms)
        if not data["binary_available"]:
            return ForgeResult.failure(TOOL, [f"Command executable not found: {data['executable']}"],
                                       timer.elapsed_ms,
                                       suggestion="Check the command name or run diag_health")
        return ForgeResult.success(TOOL, data, timer.elapsed_ms)


def _parse_command(command: str) -> list[str]:
    if not command.strip():
        raise ValueError("command is required")
    if any(token in command for token in ("\n", "\r", "\x00")):
        raise ValueError("command cannot contain control characters")
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"Invalid command quoting: {exc}") from exc
    if not tokens:
        raise ValueError("command is required")
    if any(token in SHELL_TOKENS for token in tokens):
        raise ValueError("shell operators are not accepted; provide one executable command")
    return tokens


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--command", required=True, help="One executable command; it is inspected, not executed")


if __name__ == "__main__":
    make_cli(TOOL, "Check command availability and non-interactive sudo authorization without executing it", run, _add_args)
