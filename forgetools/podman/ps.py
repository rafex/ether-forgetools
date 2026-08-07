"""forgetools.podman.ps - List Podman containers."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result
from forgetools.podman.common import target


def run(*, all: bool = False, connection: str = "", url: str = "", remote: bool = False, cwd: str | None = None) -> ForgeResult:
    podman_target = target(connection, url, remote)
    if error := podman_target.validate():
        return ForgeResult.failure("podman.ps", [error])
    cmd = podman_target.prefix() + ["ps", "--format", "json"]
    if all:
        cmd.insert(len(podman_target.prefix()) + 1, "--all")
    return command_result(tool="podman.ps", cmd=cmd, cwd=cwd, suggestion="Install podman and configure the target context.")


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--all", action="store_true", help="Include stopped containers")
    p.add_argument("--connection", default="", help="Named Podman system connection")
    p.add_argument("--url", default="", help="Podman service URL (ssh://, unix://, or tcp://)")
    p.add_argument("--remote", action="store_true", help="Use the remote Podman client")


if __name__ == "__main__":
    make_cli("podman.ps", "List Podman containers", run, _args)
