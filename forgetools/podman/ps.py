"""forgetools.podman.ps - List Podman containers."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result


def run(*, all: bool = False, cwd: str | None = None) -> ForgeResult:
    cmd = ["podman", "ps", "--format", "json"]
    if all:
        cmd.insert(2, "--all")
    return command_result(tool="podman.ps", cmd=cmd, cwd=cwd, suggestion="Install podman and configure the target context.")


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--all", action="store_true", help="Include stopped containers")


if __name__ == "__main__":
    make_cli("podman.ps", "List Podman containers", run, _args)
