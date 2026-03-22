"""forgetools.git.cherry_pick — Cherry-pick commits onto the current branch."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.cherry_pick"


def run(*, commits: str, cwd: str | None = None, no_commit: bool = False) -> ForgeResult:
    with Timer() as t:
        commit_list = commits.strip().split()
        cmd = ["git", "cherry-pick"]
        if no_commit:
            cmd.append("--no-commit")
        cmd.extend(commit_list)

        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["git not found"], suggestion="Install git")

        if rc != 0:
            conflict_files = _extract_conflicts(stderr + stdout)
            if conflict_files or "CONFLICT" in (stderr + stdout).upper():
                # Abort the cherry-pick
                run_command(["git", "cherry-pick", "--abort"], cwd=cwd)
                return ForgeResult.failure(
                    TOOL,
                    ["Cherry-pick produced conflicts; operation aborted"],
                    duration_ms=t.elapsed_ms,
                    suggestion="Resolve conflicts manually then run git cherry-pick --continue",
                )
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or "git cherry-pick failed"],
                duration_ms=t.elapsed_ms,
                suggestion="Ensure commits exist and there are no conflicts",
            )

        applied = _count_applied(stdout + stderr, commit_list)
        return ForgeResult.success(
            TOOL,
            {"commits": commit_list, "applied": applied, "conflicts": []},
            t.elapsed_ms,
        )


def _extract_conflicts(output: str) -> list[str]:
    files = []
    for line in output.splitlines():
        m = re.search(r"CONFLICT[^:]*:\s+(.+)", line)
        if m:
            files.append(m.group(1).strip())
    return files


def _count_applied(output: str, commit_list: list[str]) -> int:
    # Count lines that mention a successful cherry-pick
    count = 0
    for line in output.splitlines():
        if re.match(r"\[.+\s+[0-9a-f]+\]", line):
            count += 1
    return count if count > 0 else len(commit_list)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--commits", required=True,
                   help="Space-separated commit SHAs or range like 'abc..def'")
    p.add_argument("--no-commit", action="store_true", default=False,
                   help="Apply changes without committing")


if __name__ == "__main__":
    make_cli(TOOL, "Cherry-pick commits onto the current branch", run, _add_args)
