"""forgetools.go.mod — Run go mod commands."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "go.mod"

_VALID_ACTIONS = ("tidy", "download", "verify")


def run(*, action: str = "tidy", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        if action not in _VALID_ACTIONS:
            return ForgeResult.failure(
                TOOL,
                [f"Invalid action: {action!r}. Must be one of: {', '.join(_VALID_ACTIONS)}"],
                t.elapsed_ms,
            )
        cmd = ["go", "mod", action]
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
                [stderr.strip() or f"go mod {action} failed (rc={rc})"],
                t.elapsed_ms,
            )
        return ForgeResult.success(TOOL, {"action": action, "ok": True}, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="tidy",
                   choices=list(_VALID_ACTIONS),
                   help="go mod action to run")


if __name__ == "__main__":
    make_cli(TOOL, "Run go mod commands", run, _add_args)
