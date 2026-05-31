"""forgetools.python.mypy - Run mypy type checks."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result


def run(*, path: str = ".", extra_args: str = "", cwd: str | None = None) -> ForgeResult:
    cmd = ["mypy", path]
    if extra_args:
        cmd.extend(part for part in extra_args.split(" ") if part)
    return command_result(tool="python.mypy", cmd=cmd, cwd=cwd, suggestion="Install mypy in the active environment.")


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".", help="Target path")
    p.add_argument("--extra-args", default="", help="Extra mypy args")


if __name__ == "__main__":
    make_cli("python.mypy", "Run mypy type checks", run, _args)
