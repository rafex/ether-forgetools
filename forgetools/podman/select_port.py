"""forgetools.podman.select_port - Select the first free port in the approved bastion range."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.podman.ports import RANGES, _used_ports


def run(*, category: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        if category not in RANGES:
            return ForgeResult.failure("podman.select-port", [f"Unknown category: {category}"], t.elapsed_ms, f"Use one of: {', '.join(RANGES)}")
        try:
            used, _ = _used_ports(cwd)
        except Exception as exc:
            return ForgeResult.failure("podman.select-port", [str(exc)], t.elapsed_ms, "Run `podman ps --format '{{.Ports}}'` successfully first.")
        for port in RANGES[category]:
            if port not in used:
                return ForgeResult.success("podman.select-port", {"category": category, "port": port}, t.elapsed_ms)
        return ForgeResult.failure("podman.select-port", [f"Port range for {category} is full"], t.elapsed_ms, "Do not reuse ports; request explicit authorization.")


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--category", required=True, choices=sorted(RANGES), help="web/api/database/temporal")


if __name__ == "__main__":
    make_cli("podman.select-port", "Select first free approved bastion port", run, _args)
