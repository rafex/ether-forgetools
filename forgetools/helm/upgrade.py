"""forgetools.helm.upgrade — Upgrade (or install) a Helm release."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "helm.upgrade"


def run(
    *,
    release: str,
    chart: str,
    namespace: str = "default",
    values: str | None = None,
    set_values: str | None = None,
    install: bool = True,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["helm", "upgrade"]
        if install:
            cmd.append("--install")
        cmd.extend([release, chart, "-n", namespace])
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
                [stderr.strip() or "helm upgrade failed"],
                duration_ms=t.elapsed_ms,
                suggestion="Check chart name, namespace, and values",
            )
        deployed = "deployed" in stdout.lower() or rc == 0
        return ForgeResult.success(
            TOOL,
            {"release": release, "chart": chart, "namespace": namespace, "deployed": deployed},
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--release", required=True)
    p.add_argument("--chart", required=True)
    p.add_argument("--namespace", default="default")
    p.add_argument("--values", default=None, help="Path to values file (-f)")
    p.add_argument("--set-values", default=None, help="--set key=value overrides")
    p.add_argument("--no-install", dest="install", action="store_false", default=True,
                   help="Skip --install flag (no install if release missing)")


if __name__ == "__main__":
    make_cli(TOOL, "Upgrade (or install) a Helm release", run, _add_args)
