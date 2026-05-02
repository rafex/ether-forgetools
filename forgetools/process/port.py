"""forgetools.process.port — Check what process is using a port."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "process.port"


def run(*, port: int, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        # Try lsof first (macOS/Linux)
        data = _try_lsof(port, cwd)
        if data is None:
            # Fall back to ss (Linux)
            data = _try_ss(port, cwd)
        if data is None:
            data = {"port": port, "in_use": False, "pid": None, "process": None, "address": None}

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


def _try_lsof(port: int, cwd: str | None) -> dict | None:
    try:
        rc, stdout, _ = run_command(["lsof", "-i", f":{port}", "-n", "-P"], cwd=cwd)
    except (FileNotFoundError, Exception):
        return None

    if rc != 0 or not stdout.strip():
        return {"port": port, "in_use": False, "pid": None, "process": None, "address": None}

    lines = stdout.splitlines()
    for line in lines[1:]:  # skip header
        parts = line.split()
        if len(parts) < 9:
            continue
        process_name = parts[0]
        pid_str = parts[1]
        address = parts[8] if len(parts) > 8 else None
        try:
            pid = int(pid_str)
        except ValueError:
            pid = None
        return {"port": port, "in_use": True, "pid": pid, "process": process_name, "address": address}

    return {"port": port, "in_use": False, "pid": None, "process": None, "address": None}


def _try_ss(port: int, cwd: str | None) -> dict | None:
    try:
        rc, stdout, _ = run_command(["ss", "-tlnp", f"sport = :{port}"], cwd=cwd)
    except (FileNotFoundError, Exception):
        return None

    if rc != 0 or not stdout.strip():
        return {"port": port, "in_use": False, "pid": None, "process": None, "address": None}

    lines = stdout.splitlines()
    for line in lines[1:]:
        if str(port) in line:
            pid_match = re.search(r"pid=(\d+)", line)
            proc_match = re.search(r'"([^"]+)"', line)
            addr_match = re.search(r"\*:(\d+)|(\d+\.\d+\.\d+\.\d+):(\d+)", line)
            pid = int(pid_match.group(1)) if pid_match else None
            proc = proc_match.group(1) if proc_match else None
            addr = addr_match.group(0) if addr_match else None
            return {"port": port, "in_use": True, "pid": pid, "process": proc, "address": addr}

    return {"port": port, "in_use": False, "pid": None, "process": None, "address": None}


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--port", type=int, required=True, help="Port number to check")


if __name__ == "__main__":
    make_cli(TOOL, "Check what process is using a port", run, _add_args)
