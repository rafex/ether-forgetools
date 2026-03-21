"""forgetools.gh.pr_create — Create a GitHub pull request."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "gh.pr_create"


def run(
    *,
    cwd: str | None = None,
    title: str,
    body: str = "",
    base: str = "main",
    draft: bool = False,
    reviewer: str | None = None,
) -> ForgeResult:
    cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base]
    if draft:
        cmd.append("--draft")
    if reviewer:
        cmd += ["--reviewer", reviewer]

    return run_and_build(
        cmd, tool_name=TOOL, cwd=cwd,
        data_fn=lambda o, _: {"url": o.strip()},
        suggestion_on_fail="Authenticate with: gh auth login",
    )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--title", required=True)
    p.add_argument("--body", default="")
    p.add_argument("--base", default="main")
    p.add_argument("--draft", action="store_true")
    p.add_argument("--reviewer", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Create a GitHub pull request", run, _add_args)
