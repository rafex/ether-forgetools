"""forgetools.docker.build — Build a Docker image."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "docker.build"


def run(
    *,
    tag: str,
    dockerfile: str = "Dockerfile",
    context: str = ".",
    cwd: str | None = None,
    no_cache: bool = False,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["docker", "build", "-t", tag, "-f", dockerfile]
        if no_cache:
            cmd.append("--no-cache")
        cmd.append(context)
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["docker not found"], t.elapsed_ms,
                                       suggestion="Check Dockerfile syntax and that base image is accessible")
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"docker build failed (rc={rc})"],
                t.elapsed_ms,
                suggestion="Check Dockerfile syntax and that base image is accessible",
            )
        return ForgeResult.success(TOOL, {"tag": tag, "dockerfile": dockerfile, "context": context}, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--tag", required=True, help="Image tag (e.g. myimage:latest)")
    p.add_argument("--dockerfile", default="Dockerfile", help="Path to Dockerfile")
    p.add_argument("--context", default=".", help="Build context path")
    p.add_argument("--no-cache", action="store_true", help="Build without cache")


if __name__ == "__main__":
    make_cli(TOOL, "Build a Docker image", run, _add_args)
