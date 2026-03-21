"""forgetools.k8s.logs — Fetch Kubernetes pod logs with filters."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "k8s.logs"


def run(
    *,
    cwd: str | None = None,
    pod: str | None = None,
    deployment: str | None = None,
    namespace: str = "default",
    lines: int = 100,
    grep: str | None = None,
    container: str | None = None,
) -> ForgeResult:
    if not pod and not deployment:
        return ForgeResult.failure(TOOL, ["Provide --pod or --deployment"])

    cmd = ["kubectl", "logs", "-n", namespace, f"--tail={lines}"]
    if pod:
        cmd.append(pod)
    elif deployment:
        cmd.append(f"deployment/{deployment}")
    if container:
        cmd += ["-c", container]

    def parse(stdout: str, _stderr: str) -> dict:
        log_lines = stdout.splitlines()
        if grep:
            pattern = re.compile(grep, re.IGNORECASE)
            log_lines = [l for l in log_lines if pattern.search(l)]
        return {"line_count": len(log_lines), "lines": log_lines}

    return run_and_build(
        cmd, tool_name=TOOL, cwd=cwd, data_fn=parse,
        suggestion_on_fail="Check pod name with: forge k8s pods",
    )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pod", default=None)
    p.add_argument("--deployment", default=None)
    p.add_argument("--namespace", "-n", default="default")
    p.add_argument("--lines", type=int, default=100)
    p.add_argument("--grep", default=None)
    p.add_argument("--container", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Fetch Kubernetes pod logs", run, _add_args)
