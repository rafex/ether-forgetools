"""List Podman images on a local or remote service."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result
from forgetools.podman.common import target


def run(*, all: bool = False, connection: str = "", url: str = "", remote: bool = False, cwd: str | None = None) -> ForgeResult:
    """List images stored by the selected Podman service."""
    podman_target = target(connection, url, remote)
    if error := podman_target.validate():
        return ForgeResult.failure("podman.images", [error])
    cmd = podman_target.prefix() + ["images", "--format", "json"]
    if all:
        cmd.insert(len(podman_target.prefix()) + 1, "--all")
    return command_result("podman.images", cmd=cmd, cwd=cwd, suggestion="Verify the Podman connection and remote rootless socket")


def _args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--all", action="store_true", help="Include intermediate image layers")
    parser.add_argument("--connection", default="", help="Named Podman system connection")
    parser.add_argument("--url", default="", help="Podman service URL (ssh://, unix://, or tcp://)")
    parser.add_argument("--remote", action="store_true", help="Use the remote Podman client")


if __name__ == "__main__":
    make_cli("podman.images", "List Podman images on a local or remote service", run, _args)
