"""forgetools.docker.exec — Execute a command in a Docker container."""
from __future__ import annotations

import argparse
import shlex
import subprocess

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "docker.exec"


def run(*, container: str, cmd: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            args = ["docker", "exec", container] + shlex.split(cmd)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                cwd=cwd,
            )
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["docker not found"], t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        return ForgeResult.success(TOOL, {
            "container": container,
            "cmd": cmd,
            "stdout": result.stdout,
            "returncode": result.returncode,
        }, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--container", required=True, help="Container name or ID")
    p.add_argument("--cmd", required=True, help="Command to execute inside the container")


if __name__ == "__main__":
    make_cli(TOOL, "Execute a command in a Docker container", run, _add_args)
