"""forgetools.gh.repo_status - Aggregate repository PRs, checks, reviewers, issues, and branch state."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command


def _gh(args: list[str], cwd: str | None) -> tuple[bool, object | str]:
    rc, out, err = run_command(["gh", *args], cwd=cwd)
    if rc != 0:
        return False, err.strip() or out.strip()
    try:
        return True, json.loads(out) if out.strip() else None
    except json.JSONDecodeError:
        return False, out.strip()


def run(*, branch: str = "", limit: int = 20, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        ok_prs, prs = _gh([
            "pr", "list", "--state", "open", "--limit", str(limit),
            "--json", "number,title,author,headRefName,baseRefName,reviewDecision,reviewRequests,statusCheckRollup,url",
        ], cwd)
        ok_issues, issues = _gh([
            "issue", "list", "--state", "open", "--limit", str(limit),
            "--json", "number,title,author,labels,assignees,url",
        ], cwd)
        ok_runs, runs = _gh([
            "run", "list", "--limit", str(min(limit, 10)), "--json", "databaseId,displayTitle,headBranch,status,conclusion,url",
        ], cwd)
        ok_branches, branches = _gh([
            "api", "repos/{owner}/{repo}/branches", "--jq", ".",
        ], cwd)

        errors = []
        for name, ok, value in (("prs", ok_prs, prs), ("issues", ok_issues, issues), ("runs", ok_runs, runs), ("branches", ok_branches, branches)):
            if not ok:
                errors.append({"section": name, "error": value})

        data = {
            "branch_filter": branch or None,
            "prs": prs if ok_prs else [],
            "issues": issues if ok_issues else [],
            "runs": runs if ok_runs else [],
            "branches": branches if ok_branches else [],
            "errors": errors,
        }
        if branch and ok_prs and isinstance(prs, list):
            data["prs"] = [pr for pr in prs if pr.get("headRefName") == branch or pr.get("baseRefName") == branch]
        return ForgeResult.success("gh.repo-status", data, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--branch", default="", help="Optional PR branch filter")
    p.add_argument("--limit", type=int, default=20, help="Max PRs/issues to fetch")


if __name__ == "__main__":
    make_cli("gh.repo-status", "Aggregate repository PRs, checks, reviewers, issues, and branch state", run, _args)
