"""forgetools.helm.diff — Show diff for a Helm upgrade (requires helm-diff plugin)."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "helm.diff"

_PLUGIN_SUGGESTION = "Install helm-diff plugin: helm plugin install https://github.com/databus23/helm-diff"


def run(
    *,
    release: str,
    chart: str,
    namespace: str = "default",
    values: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["helm", "diff", "upgrade", release, chart, "-n", namespace]
        if values:
            cmd.extend(["-f", values])

        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(
                TOOL, ["helm not found"],
                duration_ms=t.elapsed_ms, suggestion=_PLUGIN_SUGGESTION
            )
        if rc != 0:
            combined = stderr.strip() or stdout.strip()
            if "unknown command" in combined.lower() or "plugin" in combined.lower():
                return ForgeResult.failure(
                    TOOL, ["helm-diff plugin not installed"],
                    duration_ms=t.elapsed_ms, suggestion=_PLUGIN_SUGGESTION
                )
            return ForgeResult.failure(
                TOOL, [combined or "helm diff failed"],
                duration_ms=t.elapsed_ms, suggestion=_PLUGIN_SUGGESTION
            )

        sections = _parse_diff(stdout)
        return ForgeResult.success(
            TOOL,
            {"has_changes": bool(sections), "sections": sections},
            t.elapsed_ms,
        )


def _parse_diff(output: str) -> list[dict]:
    sections: list[dict] = []
    current_resource: str | None = None
    current_lines: list[str] = []

    for line in output.splitlines():
        m = re.match(r"^(\S+/\S+)\s+has changed:", line)
        if not m:
            # Resource header like "default/Deployment(apps)/myapp"
            m2 = re.match(r"^([a-zA-Z].+?):", line)
            if m2 and not line.startswith(" ") and not line.startswith("+") and not line.startswith("-"):
                if current_resource is not None:
                    sections.append({"resource": current_resource, "diff": "\n".join(current_lines)})
                current_resource = line.rstrip(":")
                current_lines = []
                continue
        if current_resource is not None:
            current_lines.append(line)

    if current_resource is not None and current_lines:
        sections.append({"resource": current_resource, "diff": "\n".join(current_lines)})

    # If no structured sections, treat entire output as one block
    if not sections and output.strip():
        sections = [{"resource": "unknown", "diff": output.strip()}]

    return sections


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--release", required=True)
    p.add_argument("--chart", required=True)
    p.add_argument("--namespace", default="default")
    p.add_argument("--values", default=None, help="Path to values file (-f)")


if __name__ == "__main__":
    make_cli(TOOL, "Show Helm upgrade diff (requires helm-diff plugin)", run, _add_args)
