"""Inspect a Podman container, image, pod, or volume."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result
from forgetools.podman.common import target


def run(*, object: str, type: str = "container", connection: str = "", url: str = "", remote: bool = False, cwd: str | None = None) -> ForgeResult:
    """Inspect a Podman object on the selected local or remote service."""
    podman_target = target(connection, url, remote)
    if error := podman_target.validate():
        return ForgeResult.failure("podman.inspect", [error])
    if type not in {"container", "image", "pod", "volume", "network"}:
        return ForgeResult.failure("podman.inspect", [f"Unsupported object type: {type}"])
    cmd = podman_target.prefix() + ["inspect", "--type", type, object]
    return command_result("podman.inspect", cmd=cmd, cwd=cwd, suggestion="Verify the object name and selected Podman connection")


def _args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--object", required=True, help="Container, image, pod, volume, or network name/id")
    parser.add_argument("--type", choices=("container", "image", "pod", "volume", "network"), default="container")
    parser.add_argument("--connection", default="", help="Named Podman system connection")
    parser.add_argument("--url", default="", help="Podman service URL (ssh://, unix://, or tcp://)")
    parser.add_argument("--remote", action="store_true", help="Use the remote Podman client")


if __name__ == "__main__":
    make_cli("podman.inspect", "Inspect a Podman object on a local or remote service", run, _args)
