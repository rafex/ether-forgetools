"""forgetools.process.kill — Kill a process by PID or name."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "process.kill"


def run(
    *,
    pid: int | None = None,
    name: str | None = None,
    signal: str = "TERM",
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if pid is None and name is None:
            return ForgeResult.failure(TOOL, ["Either --pid or --name must be provided"], t.elapsed_ms)

        if pid is not None:
            cmd = ["kill", f"-{signal}", str(pid)]
        else:
            cmd = ["pkill", f"-{signal}", "-f", name]

        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError as e:
            return ForgeResult.failure(TOOL, [f"Command not found: {e}"], t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        killed = rc == 0
        return ForgeResult.success(TOOL, {
            "killed": killed,
            "pid": pid,
            "name": name,
        }, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pid", type=int, default=None, help="Process ID to kill")
    p.add_argument("--name", default=None, help="Process name pattern to kill (uses pkill -f)")
    p.add_argument("--signal", default="TERM",
                   help="Signal to send (e.g. TERM, KILL, HUP)")


if __name__ == "__main__":
    make_cli(TOOL, "Kill a process by PID or name", run, _add_args)
