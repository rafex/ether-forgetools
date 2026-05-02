"""forgetools.process.ps — List running processes."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "process.ps"


def run(*, name: str | None = None, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            rc, stdout, stderr = run_command(["ps", "aux"], cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["ps not found"], t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        if rc != 0:
            return ForgeResult.failure(TOOL, [stderr.strip() or "ps failed"], t.elapsed_ms)

        processes = _parse(stdout, name)
        return ForgeResult.success(TOOL, {"count": len(processes), "processes": processes}, t.elapsed_ms)


def _parse(output: str, name_filter: str | None) -> list[dict]:
    processes: list[dict] = []
    lines = output.splitlines()
    # Skip header line
    for line in lines[1:]:
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        try:
            proc = {
                "pid": int(parts[1]),
                "user": parts[0],
                "cpu": float(parts[2]),
                "mem": float(parts[3]),
                "command": parts[10],
            }
        except (ValueError, IndexError):
            continue

        if name_filter and name_filter.lower() not in proc["command"].lower():
            continue
        processes.append(proc)

    return processes


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--name", default=None, help="Filter processes by name (substring match)")


if __name__ == "__main__":
    make_cli(TOOL, "List running processes", run, _add_args)
