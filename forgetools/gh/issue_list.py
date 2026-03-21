"""forgetools.gh.issue_list — List GitHub issues."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "gh.issue_list"


def run(*, cwd: str | None = None, state: str = "open", label: str | None = None, limit: int = 20) -> ForgeResult:
    cmd = [
        "gh", "issue", "list",
        "--state", state,
        "--limit", str(limit),
        "--json", "number,title,author,state,labels,assignees,createdAt",
    ]
    if label:
        cmd += ["--label", label]
    return run_and_build(
        cmd, tool_name=TOOL, cwd=cwd,
        data_fn=lambda o, _: json.loads(o) if o.strip() else [],
        suggestion_on_fail="Authenticate with: gh auth login",
    )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--state", default="open", choices=["open", "closed", "all"])
    p.add_argument("--label", default=None)
    p.add_argument("--limit", type=int, default=20)


if __name__ == "__main__":
    make_cli(TOOL, "List GitHub issues", run, _add_args)
