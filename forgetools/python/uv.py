"""forgetools.python.uv - Run uv commands for Python projects."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result


def run(*, action: str = "sync", args: str = "", cwd: str | None = None) -> ForgeResult:
    cmd = ["uv", action] + ([part for part in args.split(" ") if part] if args else [])
    return command_result(tool="python.uv", cmd=cmd, cwd=cwd, suggestion="Install uv and run from a Python project.")


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="sync", help="uv subcommand: sync/run/add/remove/lock/etc")
    p.add_argument("--args", default="", help="Extra uv args as a shell-like string")


if __name__ == "__main__":
    make_cli("python.uv", "Run uv commands for Python projects", run, _args)
