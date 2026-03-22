"""forgetools.npm.run — Run an npm script."""
from __future__ import annotations

import argparse
import shlex

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "npm.run"


def run(
    *,
    script: str,
    cwd: str | None = None,
    args: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["npm", "run", script]
        if args:
            cmd += ["--"] + shlex.split(args)
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["npm not found"], t.elapsed_ms,
                                       suggestion="Check package.json scripts section")
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"npm run {script!r} failed (rc={rc})"],
                t.elapsed_ms,
                suggestion="Check package.json scripts section",
            )

        return ForgeResult.success(TOOL, {
            "script": script,
            "stdout": stdout,
            "duration_ms": t.elapsed_ms,
        }, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--script", required=True, help="npm script name to run")
    p.add_argument("--args", default=None, help="Additional arguments to pass after --")


if __name__ == "__main__":
    make_cli(TOOL, "Run an npm script", run, _add_args)
