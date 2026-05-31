"""forgetools.python.pytest - Run pytest and return structured output."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result


def run(*, path: str = "", extra_args: str = "", cwd: str | None = None) -> ForgeResult:
    cmd = ["pytest"]
    if path:
        cmd.append(path)
    if extra_args:
        cmd.extend(part for part in extra_args.split(" ") if part)
    return command_result(tool="python.pytest", cmd=cmd, cwd=cwd, suggestion="Install pytest in the active environment.")


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default="", help="Optional test path")
    p.add_argument("--extra-args", default="", help="Extra pytest args")


if __name__ == "__main__":
    make_cli("python.pytest", "Run pytest and return structured output", run, _args)
