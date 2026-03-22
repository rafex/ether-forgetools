"""forgetools.helm.install — Install a Helm chart."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "helm.install"


def run(
    *,
    release: str,
    chart: str,
    namespace: str = "default",
    values: str | None = None,
    set_values: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["helm", "install", release, chart, "-n", namespace]
        if values:
            cmd.extend(["-f", values])
        if set_values:
            cmd.extend(["--set", set_values])

        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["helm not found"], suggestion="Install Helm: https://helm.sh")
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or "helm install failed"],
                duration_ms=t.elapsed_ms,
                suggestion="Check chart name and namespace",
            )
        status = _parse_status(stdout)
        return ForgeResult.success(
            TOOL,
            {"release": release, "chart": chart, "namespace": namespace, "status": status},
            t.elapsed_ms,
        )


def _parse_status(output: str) -> str:
    m = re.search(r"STATUS:\s*(\S+)", output)
    return m.group(1) if m else "deployed"


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--release", required=True)
    p.add_argument("--chart", required=True)
    p.add_argument("--namespace", default="default")
    p.add_argument("--values", default=None, help="Path to values file (-f)")
    p.add_argument("--set-values", default=None, help="--set key=value overrides")


if __name__ == "__main__":
    make_cli(TOOL, "Install a Helm chart", run, _add_args)
