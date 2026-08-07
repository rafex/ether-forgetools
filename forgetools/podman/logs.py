"""forgetools.podman.logs - Read Podman container logs."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result
from forgetools.podman.common import target


def run(*, container: str, lines: int = 100, connection: str = "", url: str = "", remote: bool = False, cwd: str | None = None) -> ForgeResult:
    podman_target = target(connection, url, remote)
    if error := podman_target.validate():
        return ForgeResult.failure("podman.logs", [error])
    return command_result(tool="podman.logs", cmd=podman_target.prefix() + ["logs", "--tail", str(lines), container], cwd=cwd)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--container", required=True, help="Container name or id")
    p.add_argument("--lines", type=int, default=100, help="Tail lines")
    p.add_argument("--connection", default="", help="Named Podman system connection")
    p.add_argument("--url", default="", help="Podman service URL (ssh://, unix://, or tcp://)")
    p.add_argument("--remote", action="store_true", help="Use the remote Podman client")


if __name__ == "__main__":
    make_cli("podman.logs", "Read Podman container logs", run, _args)
