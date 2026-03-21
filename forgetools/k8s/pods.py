"""forgetools.k8s.pods — List Kubernetes pods with status."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "k8s.pods"


def run(
    *,
    cwd: str | None = None,
    namespace: str = "default",
    status_filter: str | None = None,
    all_namespaces: bool = False,
) -> ForgeResult:
    cmd = [
        "kubectl", "get", "pods",
        "-o", "json",
    ]
    if all_namespaces:
        cmd.append("-A")
    else:
        cmd += ["-n", namespace]

    def parse(stdout: str, _stderr: str) -> dict:
        data = json.loads(stdout)
        pods = []
        for item in data.get("items", []):
            meta = item.get("metadata", {})
            status = item.get("status", {})
            phase = status.get("phase", "Unknown")
            containers = status.get("containerStatuses", [])
            restarts = sum(c.get("restartCount", 0) for c in containers)
            ready = sum(1 for c in containers if c.get("ready", False))
            total = len(containers)
            pods.append({
                "name": meta.get("name"),
                "namespace": meta.get("namespace"),
                "phase": phase,
                "ready": f"{ready}/{total}",
                "restarts": restarts,
                "node": item.get("spec", {}).get("nodeName"),
            })
        if status_filter:
            pods = [p for p in pods if status_filter.lower() not in p["phase"].lower()]
        return {"count": len(pods), "pods": pods}

    return run_and_build(
        cmd, tool_name=TOOL, cwd=cwd, data_fn=parse,
        suggestion_on_fail="Ensure kubectl is configured: kubectl config current-context",
    )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--namespace", "-n", default="default")
    p.add_argument("--status-filter", default=None, help="Exclude pods with this phase (e.g. Running)")
    p.add_argument("--all-namespaces", "-A", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "List Kubernetes pods", run, _add_args)
