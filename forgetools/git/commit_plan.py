"""forgetools.git.commit_plan - Build an explicit multi-commit plan from changed files."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command


def _changed_files(cwd: str | None) -> list[str]:
    commands = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--staged", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    files: list[str] = []
    for cmd in commands:
        rc, out, _ = run_command(cmd, cwd=cwd)
        if rc == 0:
            files.extend(line.strip() for line in out.splitlines() if line.strip())
    return sorted(set(files))


def _group_key(path: str, mode: str) -> str:
    p = Path(path)
    if mode == "extension":
        return p.suffix.lstrip(".") or "no-extension"
    if mode == "topdir":
        return p.parts[0] if p.parts else "."
    if mode == "domain":
        first = p.parts[0] if p.parts else "."
        if first in {"tests", "test"}:
            return "tests"
        if first in {"docs", "README.md"}:
            return "docs"
        if first in {".github", ".gitlab-ci.yml"}:
            return "ci"
        return first
    return "changes"


def run(*, mode: str = "domain", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        files = _changed_files(cwd)
        if not files:
            return ForgeResult.success("git.commit-plan", {"status": "nothing_to_commit", "commits": []}, t.elapsed_ms)
        grouped: dict[str, list[str]] = defaultdict(list)
        for file in files:
            grouped[_group_key(file, mode)].append(file)
        commits = []
        for idx, (group, group_files) in enumerate(sorted(grouped.items()), start=1):
            commits.append(
                {
                    "order": idx,
                    "group": group,
                    "files": group_files,
                    "suggested_message": f"chore({group}): update {len(group_files)} file{'s' if len(group_files) != 1 else ''}",
                    "commands": [
                        "git reset",
                        *[f"git add {file}" for file in group_files],
                        f"git commit -m \"chore({group}): update {len(group_files)} file{'s' if len(group_files) != 1 else ''}\"",
                    ],
                }
            )
        return ForgeResult.success(
            "git.commit-plan",
            {"mode": mode, "files": files, "commits": commits, "note": "Plan only; execute manually after review."},
            t.elapsed_ms,
        )


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--mode", default="domain", choices=["domain", "topdir", "extension", "single"], help="Grouping strategy")


if __name__ == "__main__":
    make_cli("git.commit-plan", "Build an explicit multi-commit plan from changed files", run, _args)
