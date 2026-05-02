"""forgetools.helm.status — Helm release status."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "helm.status"


def run(*, release: str, namespace: str = "default", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            rc, stdout, stderr = run_command(
                ["helm", "status", release, "-n", namespace, "-o", "json"], cwd=cwd
            )
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["helm not found"], suggestion="Install Helm: https://helm.sh")
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"helm status failed for release '{release}'"],
                duration_ms=t.elapsed_ms,
                suggestion=f"Verify release '{release}' exists in namespace '{namespace}'",
            )
        return ForgeResult.success(TOOL, _parse(stdout), t.elapsed_ms)


def _parse(output: str) -> dict:
    try:
        obj = json.loads(output)
    except json.JSONDecodeError:
        return {"raw": output.strip()}
    info = obj.get("info", {})
    chart = obj.get("chart", {}).get("metadata", {})
    return {
        "name": obj.get("name", ""),
        "namespace": obj.get("namespace", ""),
        "status": info.get("status", ""),
        "chart": chart.get("name", ""),
        "app_version": chart.get("appVersion", ""),
        "last_deployed": info.get("last_deployed", ""),
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--release", required=True, help="Helm release name")
    p.add_argument("--namespace", default="default")


if __name__ == "__main__":
    make_cli(TOOL, "Show Helm release status", run, _add_args)
