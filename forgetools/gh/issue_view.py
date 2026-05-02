from __future__ import annotations

"""
gh/issue_view.py — View GitHub issue details, comments, and timeline (requires gh CLI + auth).

Actions:
    view        — full issue: title, body, labels, assignees, timeline, comments
    comments    — only the comments thread
    references  — issues / PRs that reference or mention this issue
"""

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "gh.issue_view"

_VIEW_FIELDS = (
    "number,title,state,body,author,labels,assignees,milestone,"
    "createdAt,updatedAt,closedAt,url,comments,reactionGroups"
)


def run(
    *,
    action: str = "view",
    number: int | None = None,
    repo:   str | None = None,     # owner/repo override (default: current git repo)
    limit:  int = 50,
    cwd:    str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if not number:
            return ForgeResult.failure(TOOL, ["--number is required"], t.elapsed_ms)

        base_cmd = ["gh", "issue"]
        repo_flag = ["--repo", repo] if repo else []

        if action == "view":
            rc, stdout, stderr = run_command(
                [*base_cmd, "view", str(number), "--json", _VIEW_FIELDS, *repo_flag],
                cwd=cwd, timeout=30,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms,
                                           suggestion="Run `gh auth login` if not authenticated")
            data = json.loads(stdout)
            # Flatten comments for readability
            comments_raw = data.pop("comments", [])
            comments = [
                {
                    "author":     (c.get("author") or {}).get("login"),
                    "body":       c.get("body"),
                    "created_at": c.get("createdAt"),
                    "url":        c.get("url"),
                }
                for c in comments_raw
            ]
            return ForgeResult.success(TOOL, {**data, "comments": comments, "comments_count": len(comments)}, t.elapsed_ms)

        if action == "comments":
            rc, stdout, stderr = run_command(
                [*base_cmd, "view", str(number), "--json", "number,comments", "--limit", str(limit), *repo_flag],
                cwd=cwd, timeout=30,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            raw = json.loads(stdout)
            comments = [
                {
                    "author":     (c.get("author") or {}).get("login"),
                    "body":       c.get("body"),
                    "created_at": c.get("createdAt"),
                    "url":        c.get("url"),
                }
                for c in raw.get("comments", [])
            ]
            return ForgeResult.success(TOOL, {"number": number, "count": len(comments), "comments": comments}, t.elapsed_ms)

        if action == "references":
            # Use gh api to get timeline and find cross-references
            endpoint = f"issues/{number}/timeline"
            if repo:
                parts = repo.split("/", 1)
                endpoint = f"repos/{repo}/issues/{number}/timeline"
            else:
                # detect from git remote
                rc2, remote_out, _ = run_command(
                    ["gh", "repo", "view", "--json", "nameWithOwner", *repo_flag],
                    cwd=cwd, timeout=15,
                )
                if rc2 == 0:
                    nwo = json.loads(remote_out).get("nameWithOwner", "")
                    if nwo:
                        endpoint = f"repos/{nwo}/issues/{number}/timeline"

            rc, stdout, stderr = run_command(
                ["gh", "api", endpoint, "--paginate",
                 "-H", "Accept: application/vnd.github.mockingbird-preview+json"],
                cwd=cwd, timeout=30,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            events = json.loads(stdout) if stdout.strip() else []
            refs = [
                {
                    "event":  e.get("event"),
                    "actor":  (e.get("actor") or {}).get("login"),
                    "source": {
                        "type":   (e.get("source") or {}).get("type"),
                        "number": ((e.get("source") or {}).get("issue") or {}).get("number"),
                        "title":  ((e.get("source") or {}).get("issue") or {}).get("title"),
                        "url":    ((e.get("source") or {}).get("issue") or {}).get("html_url"),
                    },
                    "created_at": e.get("created_at"),
                }
                for e in (events if isinstance(events, list) else [])
                if e.get("event") in ("cross-referenced", "referenced", "mentioned", "connected", "disconnected")
            ]
            return ForgeResult.success(TOOL, {"number": number, "count": len(refs), "references": refs}, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: view | comments | references"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="view", choices=["view", "comments", "references"])
    p.add_argument("--number", type=int, default=None, help="Issue number (required)")
    p.add_argument("--repo",   default=None, help="owner/repo override")
    p.add_argument("--limit",  type=int, default=50)
    p.add_argument("--cwd",    default=None)


if __name__ == "__main__":
    make_cli(TOOL, "View GitHub issue details and comments (requires gh auth)", run, _add_args)
