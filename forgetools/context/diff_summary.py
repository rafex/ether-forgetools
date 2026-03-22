"""forgetools.context.diff_summary — Summarize git diff between two refs."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "context.diff_summary"


def run(
    *,
    since: str = "HEAD~1",
    until: str = "HEAD",
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        rev_range = f"{since}..{until}"

        # Step 1: commits
        try:
            rc1, log_out, log_err = run_command(
                ["git", "log", rev_range, "--oneline"], cwd=cwd
            )
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["git not found"], suggestion="Install git")
        if rc1 != 0:
            return ForgeResult.failure(
                TOOL,
                [log_err.strip() or "git log failed"],
                duration_ms=t.elapsed_ms,
                suggestion="Verify refs exist: git log <since>..<until>",
            )

        # Step 2: stat
        rc2, stat_out, stat_err = run_command(
            ["git", "diff", "--stat", rev_range], cwd=cwd
        )
        if rc2 != 0:
            return ForgeResult.failure(
                TOOL, [stat_err.strip() or "git diff --stat failed"], duration_ms=t.elapsed_ms
            )

        # Step 3: changed files
        rc3, names_out, _ = run_command(
            ["git", "diff", "--name-only", rev_range], cwd=cwd
        )

        commits = _parse_log(log_out)
        files_changed, insertions, deletions, file_stats = _parse_stat(stat_out)
        changed_files = [f for f in names_out.strip().splitlines() if f]
        modules = _group_by_module(file_stats)
        test_files = sum(1 for f in changed_files if "test" in f.lower())

        return ForgeResult.success(TOOL, {
            "since": since,
            "until": until,
            "commits": commits,
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
            "modules": modules,
            "test_files_changed": test_files,
            "changed_files": changed_files,
        }, t.elapsed_ms)


def _parse_log(output: str) -> list[dict]:
    commits = []
    for line in output.strip().splitlines():
        if not line:
            continue
        parts = line.split(" ", 1)
        sha = parts[0]
        message = parts[1] if len(parts) > 1 else ""
        commits.append({"sha": sha, "message": message})
    return commits


def _parse_stat(output: str) -> tuple[int, int, int, list[dict]]:
    """Return (files_changed, insertions, deletions, per_file_list)."""
    files_changed = insertions = deletions = 0
    file_stats: list[dict] = []

    for line in output.strip().splitlines():
        # Summary line: " 3 files changed, 20 insertions(+), 5 deletions(-)"
        summary_m = re.search(
            r"(\d+) files? changed(?:,\s*(\d+) insertions?\(\+\))?(?:,\s*(\d+) deletions?\(-\))?",
            line,
        )
        if summary_m:
            files_changed = int(summary_m.group(1))
            insertions = int(summary_m.group(2) or 0)
            deletions = int(summary_m.group(3) or 0)
            continue

        # Per-file line: " path/file.ext | 12 ++-"
        file_m = re.match(r"^\s*(.+?)\s+\|\s+(\d+)\s+([\+\-]*)", line)
        if file_m:
            path = file_m.group(1).strip()
            changes = file_m.group(3)
            ins = changes.count("+")
            dels = changes.count("-")
            file_stats.append({"path": path, "insertions": ins, "deletions": dels})

    return files_changed, insertions, deletions, file_stats


def _group_by_module(file_stats: list[dict]) -> list[dict]:
    module_map: dict[str, dict] = {}
    for entry in file_stats:
        path = entry["path"]
        parts = path.split("/")
        module = parts[0] if len(parts) > 1 else "."
        if module not in module_map:
            module_map[module] = {"name": module, "files": 0, "insertions": 0, "deletions": 0}
        module_map[module]["files"] += 1
        module_map[module]["insertions"] += entry["insertions"]
        module_map[module]["deletions"] += entry["deletions"]
    return list(module_map.values())


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--since", default="HEAD~1", help="Start ref (default: HEAD~1)")
    p.add_argument("--until", default="HEAD", help="End ref (default: HEAD)")


if __name__ == "__main__":
    make_cli(TOOL, "Summarize git diff between two refs", run, _add_args)
