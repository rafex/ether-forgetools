"""forgetools.podman.logs - Read Podman container logs."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result


def run(*, container: str, lines: int = 100, cwd: str | None = None) -> ForgeResult:
    return command_result(tool="podman.logs", cmd=["podman", "logs", "--tail", str(lines), container], cwd=cwd)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--container", required=True, help="Container name or id")
    p.add_argument("--lines", type=int, default=100, help="Tail lines")


if __name__ == "__main__":
    make_cli("podman.logs", "Read Podman container logs", run, _args)
