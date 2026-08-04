"""Read Linux journal, kernel, and file logs with bounded output."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "linux.logs"
ACTIONS = ("journal", "dmesg", "file")


def run(*, action: str = "journal", lines: int = 100, unit: str = "", since: str = "",
        priority: str = "", path: str = "", pattern: str = "", cwd: str | None = None) -> ForgeResult:
    with Timer() as timer:
        if action not in ACTIONS:
            return ForgeResult.failure(TOOL, [f"Unknown action: {action}"], timer.elapsed_ms,
                                       suggestion=f"Use one of: {', '.join(ACTIONS)}")
        limit = max(1, min(lines, 5000))
        try:
            if action == "file":
                data = _file_log(path, limit, pattern)
            else:
                data = _command_log(action, limit, unit, since, priority, pattern, cwd)
        except (OSError, ValueError) as exc:
            return ForgeResult.failure(TOOL, [str(exc)], timer.elapsed_ms)
        return ForgeResult.success(TOOL, data, timer.elapsed_ms)


def _file_log(path: str, lines: int, pattern: str) -> dict:
    if not path:
        raise ValueError("path is required for action=file")
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise FileNotFoundError(f"Log file not found: {target}")
    selected = target.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    if pattern:
        selected = [line for line in selected if pattern.lower() in line.lower()]
    return {"source": "file", "path": str(target), "lines": selected, "count": len(selected)}


def _command_log(action: str, lines: int, unit: str, since: str, priority: str,
                 pattern: str, cwd: str | None) -> dict:
    if action == "journal":
        command = ["journalctl", "--no-pager", "--output=short-iso", f"-n{lines}"]
        if unit:
            _validate_token(unit, "unit")
            command += ["--unit", unit]
        if since:
            _validate_token(since, "since")
            command += ["--since", since]
        if priority:
            _validate_token(priority, "priority")
            command += ["--priority", priority]
    else:
        command = ["dmesg", "--color=never", "--time-format=iso"]
    if not shutil.which(command[0]):
        raise FileNotFoundError(f"{command[0]} not found")
    rc, stdout, stderr = run_command(command, cwd=cwd, timeout=30)
    if rc != 0:
        raise OSError(stderr.strip() or f"{command[0]} exited with code {rc}")
    selected = stdout.splitlines()[-lines:]
    if pattern:
        selected = [line for line in selected if pattern.lower() in line.lower()]
    return {"source": action, "command": command, "lines": selected, "count": len(selected)}


def _validate_token(value: str, name: str) -> None:
    if not value or value.startswith("-") or any(char in value for char in "\n\r\x00"):
        raise ValueError(f"Invalid {name}")


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--action", default="journal", choices=ACTIONS)
    parser.add_argument("--lines", type=int, default=100)
    parser.add_argument("--unit", default="")
    parser.add_argument("--since", default="")
    parser.add_argument("--priority", default="")
    parser.add_argument("--path", default="")
    parser.add_argument("--pattern", default="")


if __name__ == "__main__":
    make_cli(TOOL, "Read Linux journal, kernel, and file logs with bounded output", run, _add_args)
