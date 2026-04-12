from __future__ import annotations

"""
gh/pr_merge.py — Merge GitHub pull requests (requires gh CLI + auth).

Actions:
    merge   — merge a PR (merge commit | squash | rebase)
    close   — close a PR without merging
    reopen  — reopen a closed PR
    ready   — mark a draft PR as ready for review
    check   — show merge-readiness: checks status, required reviews, conflicts
"""

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "gh.pr_merge"

_MERGE_METHODS = ("merge", "squash", "rebase")


def run(
    *,
    action:       str = "merge",
    number:       int | None = None,
    method:       str = "squash",          # merge | squash | rebase
    title:        str | None = None,       # custom commit/squash title
    body:         str | None = None,       # custom commit body
    delete_branch: bool = True,
    auto:         bool = False,            # --auto: merge when checks pass
    admin:        bool = False,            # --admin: bypass branch protections
    cwd:          str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if not number:
            return ForgeResult.failure(TOOL, ["--number is required"], t.elapsed_ms)

        if action == "merge":
            if method not in _MERGE_METHODS:
                return ForgeResult.failure(
                    TOOL, [f"Invalid --method '{method}'. Use: merge | squash | rebase"], t.elapsed_ms
                )
            cmd = ["gh", "pr", "merge", str(number), f"--{method}"]
            if delete_branch:
                cmd.append("--delete-branch")
            if title:
                cmd += ["--subject", title]
            if body:
                cmd += ["--body", body]
            if auto:
                cmd.append("--auto")
            if admin:
                cmd.append("--admin")

            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=60)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip() or f"gh pr merge failed (rc={rc})"],
                                           t.elapsed_ms,
                                           suggestion="Check branch protections or required reviews")
            return ForgeResult.success(TOOL, {
                "merged":         True,
                "number":         number,
                "method":         method,
                "branch_deleted": delete_branch,
                "auto":           auto,
            }, t.elapsed_ms)

        if action == "close":
            cmd = ["gh", "pr", "close", str(number)]
            if body:
                cmd += ["--comment", body]
            if delete_branch:
                cmd.append("--delete-branch")
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=30)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"closed": True, "number": number}, t.elapsed_ms)

        if action == "reopen":
            rc, stdout, stderr = run_command(["gh", "pr", "reopen", str(number)], cwd=cwd, timeout=30)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"reopened": True, "number": number}, t.elapsed_ms)

        if action == "ready":
            rc, stdout, stderr = run_command(["gh", "pr", "ready", str(number)], cwd=cwd, timeout=30)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"ready": True, "number": number}, t.elapsed_ms)

        if action == "check":
            fields = "number,title,state,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,isDraft,headRefName,baseRefName"
            rc, stdout, stderr = run_command(
                ["gh", "pr", "view", str(number), "--json", fields],
                cwd=cwd, timeout=30,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            data = json.loads(stdout)

            checks = data.get("statusCheckRollup") or []
            failed = [c for c in checks if c.get("conclusion") in ("FAILURE", "TIMED_OUT", "CANCELLED")]
            pending = [c for c in checks if c.get("status") in ("IN_PROGRESS", "QUEUED", "WAITING")]
            passed  = [c for c in checks if c.get("conclusion") == "SUCCESS"]

            ready_to_merge = (
                data.get("mergeable") == "MERGEABLE"
                and data.get("reviewDecision") in ("APPROVED", None)
                and not failed
                and not pending
                and not data.get("isDraft")
            )

            return ForgeResult.success(TOOL, {
                "number":           data["number"],
                "title":            data.get("title"),
                "state":            data.get("state"),
                "draft":            data.get("isDraft"),
                "mergeable":        data.get("mergeable"),
                "merge_state":      data.get("mergeStateStatus"),
                "review_decision":  data.get("reviewDecision"),
                "head_branch":      data.get("headRefName"),
                "base_branch":      data.get("baseRefName"),
                "ready_to_merge":   ready_to_merge,
                "checks": {
                    "total":   len(checks),
                    "passed":  len(passed),
                    "failed":  len(failed),
                    "pending": len(pending),
                    "failures": [{"name": c.get("name"), "url": c.get("detailsUrl")} for c in failed],
                },
            }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: merge | close | reopen | ready | check"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="merge",
                   choices=["merge", "close", "reopen", "ready", "check"])
    p.add_argument("--number", type=int, default=None, help="PR number (required)")
    p.add_argument("--method", default="squash", choices=["merge", "squash", "rebase"],
                   help="Merge strategy (default: squash)")
    p.add_argument("--title",  default=None, help="Custom commit/squash title")
    p.add_argument("--body",   default=None, help="Custom commit body")
    p.add_argument("--no-delete-branch", action="store_false", dest="delete_branch",
                   help="Keep the head branch after merge")
    p.add_argument("--auto",   action="store_true", help="Merge when all checks pass")
    p.add_argument("--admin",  action="store_true", help="Bypass branch protections")
    p.add_argument("--cwd",    default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Merge GitHub pull requests (requires gh auth)", run, _add_args)
