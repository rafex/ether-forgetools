"""forgetools.docker.ps — List Docker containers."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "docker.ps"


def run(*, all: bool = False, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        cmd = ["docker", "ps", "--format", "json"]
        if all:
            cmd.insert(2, "--all")
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["docker not found"], t.elapsed_ms,
                                       suggestion="Install Docker: https://docs.docker.com/get-docker/")
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        if rc != 0:
            return ForgeResult.failure(TOOL, [stderr.strip() or f"docker ps failed (rc={rc})"], t.elapsed_ms)

        try:
            data = _parse(stdout)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Failed to parse docker output: {e}"], t.elapsed_ms)


def _parse(output: str) -> dict:
    containers: list[dict] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        containers.append({
            "id": obj.get("ID", obj.get("Id", "")),
            "image": obj.get("Image", ""),
            "name": obj.get("Names", obj.get("Name", "")),
            "status": obj.get("Status", ""),
            "ports": obj.get("Ports", ""),
            "created": obj.get("CreatedAt", obj.get("Created", "")),
        })
    return {"count": len(containers), "containers": containers}


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--all", action="store_true", help="Show all containers (including stopped)")


if __name__ == "__main__":
    make_cli(TOOL, "List Docker containers", run, _add_args)
