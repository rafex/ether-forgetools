"""forgetools.podman.validate_ports - Validate Podman port publications against bastion policy."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.podman.ports import RANGES

PORT_FLAG_RE = re.compile(r"(?:-p|--publish)\s+([0-9]+):")
COMPOSE_PORT_RE = re.compile(r"['\"]?([0-9]+):[0-9]+")
ALLOWED = set().union(*(set(r) for r in RANGES.values()))


def run(*, file: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        path = (Path(cwd or ".") / file).resolve()
        text = path.read_text(encoding="utf-8", errors="ignore")
        ports = [int(p) for p in PORT_FLAG_RE.findall(text)]
        ports += [int(p) for p in COMPOSE_PORT_RE.findall(text)]
        violations = [p for p in sorted(set(ports)) if p not in ALLOWED]
        return ForgeResult.success(
            "podman.validate-ports",
            {
                "file": str(path),
                "ports": sorted(set(ports)),
                "violations": violations,
                "ok": not violations,
                "policy": {name: f"{min(values)}-{max(values)}" for name, values in RANGES.items()},
            },
            t.elapsed_ms,
        )


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True, help="Script, compose file, Containerfile, or manifest to validate")


if __name__ == "__main__":
    make_cli("podman.validate-ports", "Validate Podman port publications against bastion policy", run, _args)
