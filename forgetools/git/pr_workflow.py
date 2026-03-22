"""forgetools.git.pr_workflow — Create a GitHub PR via branch + push + gh pr create."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.pr_workflow"


def run(
    *,
    branch: str,
    title: str,
    body: str = "",
    base: str = "main",
    cwd: str | None = None,
    draft: bool = False,
) -> ForgeResult:
    with Timer() as t:
        # Step 1: checkout or create branch
        rc, stdout, stderr = run_command(["git", "checkout", "-b", branch], cwd=cwd)
        if rc != 0:
            # Branch might already exist — try switching to it
            rc2, _, stderr2 = run_command(["git", "checkout", branch], cwd=cwd)
            if rc2 != 0:
                return ForgeResult.failure(
                    TOOL,
                    [stderr2.strip() or f"Failed to checkout branch: {branch}"],
                    t.elapsed_ms,
                    suggestion="Stage and commit changes before calling pr_workflow",
                )

        # Step 2: push branch
        rc, _, stderr = run_command(["git", "push", "-u", "origin", branch], cwd=cwd)
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"Failed to push branch: {branch}"],
                t.elapsed_ms,
                suggestion="Stage and commit changes before calling pr_workflow",
            )

        # Step 3: create PR
        cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base]
        if draft:
            cmd.append("--draft")
        rc, stdout, stderr = run_command(cmd, cwd=cwd)
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or "gh pr create failed"],
                t.elapsed_ms,
                suggestion="Stage and commit changes before calling pr_workflow",
            )

        pr_url = _parse_pr_url(stdout)
        return ForgeResult.success(TOOL, {
            "branch": branch,
            "pr_url": pr_url,
            "title": title,
            "base": base,
        }, t.elapsed_ms)


def _parse_pr_url(output: str) -> str:
    m = re.search(r"https://github\.com/[^\s]+", output)
    return m.group(0) if m else output.strip()


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--branch", required=True, help="Branch name to create/use")
    p.add_argument("--title", required=True, help="PR title")
    p.add_argument("--body", default="", help="PR body text")
    p.add_argument("--base", default="main", help="Base branch for the PR")
    p.add_argument("--draft", action="store_true", help="Create as draft PR")


if __name__ == "__main__":
    make_cli(TOOL, "Create a GitHub PR", run, _add_args)
