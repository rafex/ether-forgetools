"""forgetools.gh.pr_review — View PR review comments and status."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "gh.pr_review"


def run(*, cwd: str | None = None, number: int) -> ForgeResult:
    cmd = [
        "gh", "pr", "view", str(number),
        "--json", "number,title,state,body,reviews,comments,statusCheckRollup,reviewDecision",
    ]
    return run_and_build(
        cmd, tool_name=TOOL, cwd=cwd,
        data_fn=lambda o, _: json.loads(o),
        suggestion_on_fail="Authenticate with: gh auth login",
    )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--number", type=int, required=True)


if __name__ == "__main__":
    make_cli(TOOL, "View PR review status and comments", run, _add_args)
