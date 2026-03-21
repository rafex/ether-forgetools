"""forgetools.k8s.rollout — Manage Kubernetes rollouts."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "k8s.rollout"


def run(
    *,
    cwd: str | None = None,
    deployment: str,
    namespace: str = "default",
    action: str = "status",
) -> ForgeResult:
    if action not in ("status", "undo", "restart", "history"):
        return ForgeResult.failure(TOOL, [f"Unknown action: {action}"], suggestion="Use: status, undo, restart, history")

    cmd = ["kubectl", "rollout", action, f"deployment/{deployment}", "-n", namespace]
    return run_and_build(
        cmd, tool_name=TOOL, cwd=cwd,
        data_fn=lambda o, _: {"output": o.strip()},
        suggestion_on_fail="Ensure kubectl is configured",
    )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--deployment", required=True)
    p.add_argument("--namespace", "-n", default="default")
    p.add_argument("--action", default="status", choices=["status", "undo", "restart", "history"])


if __name__ == "__main__":
    make_cli(TOOL, "Manage Kubernetes deployment rollouts", run, _add_args)
