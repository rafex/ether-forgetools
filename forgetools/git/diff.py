"""forgetools.git.diff — Git diff with structured output."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "git.diff"


def run(
    *,
    cwd: str | None = None,
    staged: bool = False,
    commit: str | None = None,
    path: str | None = None,
) -> ForgeResult:
    cmd = ["git", "diff", "--stat", "--patch"]
    if staged:
        cmd.append("--staged")
    if commit:
        cmd.append(commit)
    if path:
        cmd += ["--", path]

    return run_and_build(
        cmd,
        tool_name=TOOL,
        cwd=cwd,
        data_fn=_parse,
        suggestion_on_fail="Run inside a git repository",
    )


def _parse(stdout: str, _stderr: str) -> dict:
    files: list[dict] = []
    current: dict | None = None
    hunks: list[str] = []

    for line in stdout.splitlines():
        if line.startswith("diff --git"):
            if current is not None:
                current["patch"] = "\n".join(hunks)
                files.append(current)
            m = re.search(r"b/(.+)$", line)
            current = {"file": m.group(1) if m else line, "added": 0, "removed": 0, "patch": ""}
            hunks = [line]
        elif current is not None:
            hunks.append(line)
            if line.startswith("+") and not line.startswith("+++"):
                current["added"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                current["removed"] += 1

    if current is not None:
        current["patch"] = "\n".join(hunks)
        files.append(current)

    total_added = sum(f["added"] for f in files)
    total_removed = sum(f["removed"] for f in files)
    return {"files": files, "total_added": total_added, "total_removed": total_removed}


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--staged", action="store_true")
    p.add_argument("--commit", default=None)
    p.add_argument("--path", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Show git diff", run, _add_args)
