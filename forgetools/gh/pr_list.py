"""forgetools.gh.pr_list — List GitHub pull requests."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "gh.pr_list"


def run(*, cwd: str | None = None, state: str = "open", limit: int = 20) -> ForgeResult:
    cmd = [
        "gh", "pr", "list",
        "--state", state,
        "--limit", str(limit),
        "--json", "number,title,author,state,createdAt,headRefName,reviewDecision,statusCheckRollup",
    ]
    return run_and_build(
        cmd, tool_name=TOOL, cwd=cwd,
        data_fn=lambda o, _: json.loads(o) if o.strip() else [],
        suggestion_on_fail="Authenticate with: gh auth login",
    )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--state", default="open", choices=["open", "closed", "merged", "all"])
    p.add_argument("--limit", type=int, default=20)


if __name__ == "__main__":
    make_cli(TOOL, "List GitHub pull requests", run, _add_args)
