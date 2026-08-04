"""Inspect Linux host identity, CPU, memory, uptime, and resource limits."""
from __future__ import annotations

import argparse
import os
import platform
import resource
import time
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "linux.system"
ACTIONS = ("info", "cpu", "memory", "uptime", "limits")


def run(*, action: str = "info", cwd: str | None = None) -> ForgeResult:
    with Timer() as timer:
        if action not in ACTIONS:
            return ForgeResult.failure(TOOL, [f"Unknown action: {action}"], timer.elapsed_ms,
                                       suggestion=f"Use one of: {', '.join(ACTIONS)}")
        try:
            if action == "info":
                data = _info()
            elif action == "cpu":
                data = _cpu()
            elif action == "memory":
                data = _memory()
            elif action == "uptime":
                data = _uptime()
            else:
                data = _limits()
        except OSError as exc:
            return ForgeResult.failure(TOOL, [str(exc)], timer.elapsed_ms)
        return ForgeResult.success(TOOL, data, timer.elapsed_ms)


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for line in _read("/etc/os-release").splitlines():
            if "=" not in line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    except FileNotFoundError:
        pass
    return values


def _info() -> dict:
    return {
        "hostname": platform.node(),
        "kernel": platform.release(),
        "system": platform.system(),
        "architecture": platform.machine(),
        "os_release": _os_release(),
        "cpu": _cpu(),
        "memory": _memory(),
        "uptime": _uptime(),
    }


def _cpu() -> dict:
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    return {
        "logical_cpus": os.cpu_count() or 1,
        "load_average": {"1m": load[0], "5m": load[1], "15m": load[2]},
    }


def _memory() -> dict:
    values: dict[str, int] = {}
    try:
        for line in _read("/proc/meminfo").splitlines():
            key, _, raw = line.partition(":")
            parts = raw.strip().split()
            if parts and parts[0].isdigit():
                values[key] = int(parts[0]) * (1024 if len(parts) > 1 and parts[1] == "kB" else 1)
    except FileNotFoundError:
        return {"available": False}
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", values.get("MemFree", 0))
    swap_total = values.get("SwapTotal", 0)
    swap_free = values.get("SwapFree", 0)
    return {
        "available": bool(total),
        "total_bytes": total,
        "available_bytes": available,
        "used_bytes": max(total - available, 0),
        "swap_total_bytes": swap_total,
        "swap_free_bytes": swap_free,
        "swap_used_bytes": max(swap_total - swap_free, 0),
    }


def _uptime() -> dict:
    try:
        seconds = float(_read("/proc/uptime").split()[0])
        source = "/proc/uptime"
    except (FileNotFoundError, IndexError, ValueError):
        seconds = time.monotonic()
        source = "monotonic-fallback"
    return {"seconds": seconds, "source": source}


def _limits() -> dict:
    limits = {}
    for name, constant in {
        "open_files": resource.RLIMIT_NOFILE,
        "processes": resource.RLIMIT_NPROC,
        "locked_memory": resource.RLIMIT_MEMLOCK,
    }.items():
        soft, hard = resource.getrlimit(constant)
        limits[name] = {"soft": soft, "hard": hard}
    try:
        limits["file_nr"] = _read("/proc/sys/fs/file-nr").split()
    except FileNotFoundError:
        pass
    return limits


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--action", default="info", choices=ACTIONS)


if __name__ == "__main__":
    make_cli(TOOL, "Inspect Linux host identity, CPU, memory, uptime, and limits", run, _add_args)
