"""forgetools.docker.logs — Fetch Docker container logs."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "docker.logs"


def run(*, container: str, tail: int = 100, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        cmd = ["docker", "logs", "--tail", str(tail), container]
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["docker not found"], t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"docker logs failed (rc={rc})"],
                t.elapsed_ms,
            )

        # Docker logs may go to stderr (normal behavior for some containers)
        combined = stdout or stderr
        lines = combined.splitlines()
        return ForgeResult.success(TOOL, {"container": container, "lines": lines, "count": len(lines)}, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--container", required=True, help="Container name or ID")
    p.add_argument("--tail", type=int, default=100, help="Number of lines to fetch")


if __name__ == "__main__":
    make_cli(TOOL, "Fetch Docker container logs", run, _add_args)
