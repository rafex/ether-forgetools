"""forgetools.git.status — Git repository status."""
from __future__ import annotations

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.status"


def run(*, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            rc, stdout, stderr = run_command(
                ["git", "status", "--porcelain=v2", "--branch"], cwd=cwd
            )
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["git not found"], suggestion="Install git")
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or "git status failed"],
                duration_ms=t.elapsed_ms,
                suggestion="Run inside a git repository",
            )
        return ForgeResult.success(TOOL, _parse(stdout), t.elapsed_ms)


def _parse(output: str) -> dict:
    branch = upstream = None
    ahead = behind = 0
    staged, unstaged, untracked, conflicted = [], [], [], []

    for line in output.splitlines():
        if line.startswith("# branch.head"):
            branch = line.split()[-1]
        elif line.startswith("# branch.upstream"):
            upstream = line.split()[-1]
        elif line.startswith("# branch.ab"):
            for p in line.split():
                if p.startswith("+"):
                    ahead = int(p[1:])
                elif p.startswith("-"):
                    behind = int(p[1:])
        elif line.startswith("1 ") or line.startswith("2 "):
            parts = line.split(" ", 8)
            xy = parts[1]
            path = parts[-1].split("\t")[-1] if "\t" in parts[-1] else parts[-1]
            x, y = xy[0], xy[1]
            if x not in (".", "?"):
                staged.append({"path": path, "status": x})
            if y not in (".", "?"):
                unstaged.append({"path": path, "status": y})
            if x == "U" or y == "U" or (x == y == "A") or (x == y == "D"):
                conflicted.append(path)
        elif line.startswith("? "):
            untracked.append(line[2:])

    return {
        "branch": branch,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "conflicted": conflicted,
        "is_clean": not any([staged, unstaged, untracked, conflicted]),
    }


if __name__ == "__main__":
    make_cli(TOOL, "Show git repository status", run)
