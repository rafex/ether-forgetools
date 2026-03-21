"""forgetools.git.conflicts — List conflicted files."""
from __future__ import annotations

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "git.conflicts"


def run(*, cwd: str | None = None) -> ForgeResult:
    return run_and_build(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        tool_name=TOOL,
        cwd=cwd,
        data_fn=lambda o, _: {"conflicted": [f for f in o.splitlines() if f.strip()]},
        suggestion_on_fail="Run inside a git repository",
    )


if __name__ == "__main__":
    make_cli(TOOL, "List conflicted files", run)
