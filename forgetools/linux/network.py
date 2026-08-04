"""Inspect Linux interfaces, routes, DNS, and socket connections."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "linux.network"
ACTIONS = ("interfaces", "routes", "dns", "connections")


def run(*, action: str = "interfaces", cwd: str | None = None) -> ForgeResult:
    with Timer() as timer:
        if action not in ACTIONS:
            return ForgeResult.failure(TOOL, [f"Unknown action: {action}"], timer.elapsed_ms,
                                       suggestion=f"Use one of: {', '.join(ACTIONS)}")
        try:
            if action == "dns":
                data = _dns(cwd)
            else:
                data = _ip_action(action, cwd)
        except (OSError, ValueError) as exc:
            return ForgeResult.failure(TOOL, [str(exc)], timer.elapsed_ms)
        return ForgeResult.success(TOOL, data, timer.elapsed_ms)


def _ip_action(action: str, cwd: str | None) -> dict:
    if action in {"interfaces", "routes"} and shutil.which("ip"):
        command = ["ip", "-j", "addr" if action == "interfaces" else "route"]
        rc, stdout, stderr = run_command(command, cwd=cwd, timeout=20)
        if rc != 0:
            raise OSError(stderr.strip() or f"ip exited with code {rc}")
        try:
            return {"action": action, "backend": "ip-json", "items": json.loads(stdout)}
        except json.JSONDecodeError:
            return {"action": action, "backend": "ip", "output": stdout.strip()}
    if action == "connections" and shutil.which("ss"):
        command = ["ss", "-H", "-tunap"]
        rc, stdout, stderr = run_command(command, cwd=cwd, timeout=20)
        if rc != 0:
            raise OSError(stderr.strip() or f"ss exited with code {rc}")
        return {"action": action, "backend": "ss", "connections": stdout.splitlines()}
    raise FileNotFoundError("Required Linux network command not found (ip or ss)")


def _dns(cwd: str | None) -> dict:
    resolv = Path("/etc/resolv.conf")
    nameservers = []
    search = []
    if resolv.is_file():
        for line in resolv.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "nameserver":
                nameservers.append(parts[1])
            elif len(parts) >= 2 and parts[0] == "search":
                search.extend(parts[1:])
    data = {"nameservers": nameservers, "search_domains": search, "resolv_conf": str(resolv)}
    if shutil.which("resolvectl"):
        rc, stdout, stderr = run_command(["resolvectl", "status"], cwd=cwd, timeout=20)
        data["resolvectl"] = stdout.strip() if rc == 0 else stderr.strip()
    return data


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--action", default="interfaces", choices=ACTIONS)


if __name__ == "__main__":
    make_cli(TOOL, "Inspect Linux interfaces, routes, DNS, and socket connections", run, _add_args)
