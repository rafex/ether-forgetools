"""forgetools.git.branch — List and manage git branches."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "git.branch"


def run(*, cwd: str | None = None, all: bool = False) -> ForgeResult:
    cmd = ["git", "branch", "-vv"]
    if all:
        cmd.append("-a")
    return run_and_build(
        cmd,
        tool_name=TOOL,
        cwd=cwd,
        data_fn=_parse,
        suggestion_on_fail="Run inside a git repository",
    )


def _parse(stdout: str, _stderr: str) -> dict:
    branches = []
    current = None
    for line in stdout.splitlines():
        is_current = line.startswith("*")
        line = line.lstrip("* ").strip()
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        tracking = None
        if len(parts) > 2 and parts[2].startswith("["):
            tracking = parts[2].strip("[]").split(":")[0]
        entry = {"name": name, "is_current": is_current, "tracking": tracking}
        branches.append(entry)
        if is_current:
            current = name
    return {"current": current, "branches": branches}


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--all", action="store_true", help="Show remote branches too")


if __name__ == "__main__":
    make_cli(TOOL, "List git branches", run, _add_args)
