"""forgetools.k8s.contexts — List and switch kubectl contexts."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "k8s.contexts"


def run(*, cwd: str | None = None, switch_to: str | None = None) -> ForgeResult:
    if switch_to:
        cmd = ["kubectl", "config", "use-context", switch_to]
        return run_and_build(cmd, tool_name=TOOL, cwd=cwd, data_fn=lambda o, _: {"output": o.strip()})

    cmd = ["kubectl", "config", "get-contexts"]
    return run_and_build(cmd, tool_name=TOOL, cwd=cwd, data_fn=_parse)


def _parse(stdout: str, _stderr: str) -> dict:
    contexts = []
    current = None
    for line in stdout.splitlines()[1:]:  # skip header
        parts = line.split()
        if not parts:
            continue
        is_current = parts[0] == "*"
        if is_current:
            parts = parts[1:]
        name = parts[0] if parts else ""
        if is_current:
            current = name
        contexts.append({"name": name, "is_current": is_current})
    return {"current": current, "contexts": contexts}


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--switch-to", default=None, help="Switch to this context")


if __name__ == "__main__":
    make_cli(TOOL, "List and switch kubectl contexts", run, _add_args)
