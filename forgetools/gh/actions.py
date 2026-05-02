"""forgetools.gh.actions — GitHub Actions workflow status."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "gh.actions"


def run(*, cwd: str | None = None, branch: str | None = None, limit: int = 10) -> ForgeResult:
    cmd = [
        "gh", "run", "list",
        "--limit", str(limit),
        "--json", "databaseId,name,status,conclusion,headBranch,createdAt,url",
    ]
    if branch:
        cmd += ["--branch", branch]
    return run_and_build(
        cmd, tool_name=TOOL, cwd=cwd,
        data_fn=lambda o, _: json.loads(o) if o.strip() else [],
        suggestion_on_fail="Authenticate with: gh auth login",
    )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--branch", default=None)
    p.add_argument("--limit", type=int, default=10)


if __name__ == "__main__":
    make_cli(TOOL, "List GitHub Actions runs", run, _add_args)
