"""forgetools.podman.validate_ports - Validate Podman port publications against bastion policy."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.podman.common import validate_publications
from forgetools.podman.ports import RANGES

PORT_FLAG_RE = re.compile(r"(?:-p|--publish)(?:=|\s+)([^\s]+)")
COMPOSE_PORT_RE = re.compile(r"['\"]?((?:[0-9]+:)?[0-9]+:[0-9]+(?:/(?:tcp|udp|sctp))?)['\"]?")
ALLOWED = set().union(*(set(r) for r in RANGES.values()))


def run(*, file: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        path = (Path(cwd or ".") / file).resolve()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return ForgeResult.failure("podman.validate-ports", [str(exc)], t.elapsed_ms, "Provide a readable Containerfile, compose file, script, or manifest")
        publications = PORT_FLAG_RE.findall(text)
        publications += COMPOSE_PORT_RE.findall(text)
        parsed, errors = validate_publications(publications)
        ports = sorted({int(item["host_port"]) for item in parsed})
        violations = sorted({port for item in parsed if item.get("category") == "forbidden" for port in [int(item["host_port"])]})
        return ForgeResult.success(
            "podman.validate-ports",
            {
                "file": str(path),
                "ports": sorted(set(ports)),
                "violations": violations,
                "errors": errors,
                "ok": not violations and not errors,
                "policy": {name: f"{min(values)}-{max(values)}" for name, values in RANGES.items()},
            },
            t.elapsed_ms,
        )


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True, help="Script, compose file, Containerfile, or manifest to validate")


if __name__ == "__main__":
    make_cli("podman.validate-ports", "Validate Podman port publications against bastion policy", run, _args)
