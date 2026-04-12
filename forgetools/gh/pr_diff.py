from __future__ import annotations

"""
gh/pr_diff.py — Files changed in a GitHub PR (requires gh CLI + auth).

Actions:
    files   — list of files changed with status and additions/deletions
    diff    — raw unified diff of the PR
    stat    — summary stats: total files, additions, deletions, changed lines
"""

import argparse
import json
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "gh.pr_diff"


def run(
    *,
    action:  str = "files",
    number:  int | None = None,
    patch:   bool = False,        # include patch text in files action
    cwd:     str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if not number:
            return ForgeResult.failure(TOOL, ["--number is required"], t.elapsed_ms)

        if action == "files":
            fields = "files"
            rc, stdout, stderr = run_command(
                ["gh", "pr", "view", str(number), "--json", fields],
                cwd=cwd, timeout=30,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms,
                                           suggestion="Run `gh auth login` if not authenticated")
            data = json.loads(stdout)
            files = data.get("files") or []
            result_files = [
                {
                    "path":       f.get("path"),
                    "status":     f.get("additions", 0) > 0 and f.get("deletions", 0) > 0 and "modified"
                                  or f.get("additions", 0) > 0 and "added"
                                  or "deleted",
                    "additions":  f.get("additions", 0),
                    "deletions":  f.get("deletions", 0),
                    "changes":    f.get("additions", 0) + f.get("deletions", 0),
                    **({"patch": f.get("patch")} if patch else {}),
                }
                for f in files
            ]
            total_add = sum(f["additions"] for f in result_files)
            total_del = sum(f["deletions"] for f in result_files)
            return ForgeResult.success(TOOL, {
                "number":     number,
                "file_count": len(result_files),
                "additions":  total_add,
                "deletions":  total_del,
                "files":      result_files,
            }, t.elapsed_ms)

        if action == "diff":
            rc, stdout, stderr = run_command(
                ["gh", "pr", "diff", str(number)],
                cwd=cwd, timeout=60,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)

            # Parse diff for file stats
            file_headers = re.findall(r"^diff --git a/(.+) b/(.+)$", stdout, re.MULTILINE)
            additions = len(re.findall(r"^\+(?!\+\+)", stdout, re.MULTILINE))
            deletions = len(re.findall(r"^-(?!--)", stdout, re.MULTILINE))

            return ForgeResult.success(TOOL, {
                "number":     number,
                "file_count": len(file_headers),
                "additions":  additions,
                "deletions":  deletions,
                "diff":       stdout,
            }, t.elapsed_ms)

        if action == "stat":
            rc, stdout, stderr = run_command(
                ["gh", "pr", "view", str(number), "--json", "files,additions,deletions"],
                cwd=cwd, timeout=30,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            data = json.loads(stdout)
            files = data.get("files") or []
            by_ext: dict[str, int] = {}
            for f in files:
                path = f.get("path", "")
                ext = path.rsplit(".", 1)[-1] if "." in path else "(none)"
                by_ext[ext] = by_ext.get(ext, 0) + 1
            return ForgeResult.success(TOOL, {
                "number":       number,
                "file_count":   len(files),
                "additions":    data.get("additions", sum(f.get("additions", 0) for f in files)),
                "deletions":    data.get("deletions", sum(f.get("deletions", 0) for f in files)),
                "by_extension": dict(sorted(by_ext.items(), key=lambda x: -x[1])),
            }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: files | diff | stat"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="files", choices=["files", "diff", "stat"])
    p.add_argument("--number", type=int, default=None, help="PR number (required)")
    p.add_argument("--patch",  action="store_true", help="Include patch text in files action")
    p.add_argument("--cwd",    default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Files changed in a GitHub PR (requires gh auth)", run, _add_args)
