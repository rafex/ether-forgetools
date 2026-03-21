"""forgetools.diag.port_check — Check if a port is in use."""
from __future__ import annotations

import argparse
import socket
import subprocess

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "diag.port_check"


def run(*, cwd: str | None = None, port: int, host: str = "localhost") -> ForgeResult:
    with Timer() as t:
        in_use = _is_port_in_use(host, port)
        pid = _get_pid(port) if in_use else None
        return ForgeResult.success(
            TOOL,
            {"port": port, "host": host, "in_use": in_use, "pid": pid},
            t.elapsed_ms,
        )


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


def _get_pid(port: int) -> int | None:
    try:
        result = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            capture_output=True, text=True, timeout=5,
        )
        return int(result.stdout.strip()) if result.stdout.strip() else None
    except Exception:
        return None


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--host", default="localhost")


if __name__ == "__main__":
    make_cli(TOOL, "Check if a port is in use", run, _add_args)
