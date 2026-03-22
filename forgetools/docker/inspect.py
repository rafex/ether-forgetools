"""forgetools.docker.inspect — Inspect a Docker container."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "docker.inspect"


def run(*, container: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        cmd = ["docker", "inspect", container]
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["docker not found"], t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"docker inspect failed (rc={rc})"],
                t.elapsed_ms,
            )

        try:
            items = json.loads(stdout)
            if not items:
                return ForgeResult.failure(TOOL, [f"No container found: {container}"], t.elapsed_ms)
            return ForgeResult.success(TOOL, items[0], t.elapsed_ms)
        except json.JSONDecodeError as e:
            return ForgeResult.failure(TOOL, [f"Failed to parse docker inspect output: {e}"], t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--container", required=True, help="Container name or ID")


if __name__ == "__main__":
    make_cli(TOOL, "Inspect a Docker container", run, _add_args)
