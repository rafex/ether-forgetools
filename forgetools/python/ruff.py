"""forgetools.python.ruff - Run ruff check/format."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result


def run(*, action: str = "check", path: str = ".", extra_args: str = "", cwd: str | None = None) -> ForgeResult:
    cmd = ["ruff", action, path]
    if extra_args:
        cmd.extend(part for part in extra_args.split(" ") if part)
    return command_result(tool="python.ruff", cmd=cmd, cwd=cwd, suggestion="Install ruff in the active environment.")


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="check", help="ruff action: check or format")
    p.add_argument("--path", default=".", help="Target path")
    p.add_argument("--extra-args", default="", help="Extra ruff args")


if __name__ == "__main__":
    make_cli("python.ruff", "Run ruff check/format", run, _args)
