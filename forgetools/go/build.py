"""forgetools.go.build — Run go build."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "go.build"


def run(
    *,
    path: str = "./...",
    cwd: str | None = None,
    output: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["go", "build"]
        if output:
            cmd += ["-o", output]
        cmd.append(path)
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["go not found"], t.elapsed_ms,
                                       suggestion="Install Go: https://go.dev/doc/install")
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"go build failed (rc={rc})"],
                t.elapsed_ms,
            )
        return ForgeResult.success(TOOL, {"path": path, "output": output, "ok": True}, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default="./...", help="Package path to build")
    p.add_argument("--output", default=None, help="Output binary path")


if __name__ == "__main__":
    make_cli(TOOL, "Run go build", run, _add_args)
