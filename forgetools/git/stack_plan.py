"""forgetools.git.stack_plan - Plan stacked PR branches from ordered task names."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-") or "task"


def _current_branch(cwd: str | None) -> str:
    rc, out, _ = run_command(["git", "branch", "--show-current"], cwd=cwd)
    return out.strip() if rc == 0 else ""


def run(*, tasks: str, base: str = "", prefix: str = "stack", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        task_list = [_slug(item.strip()) for item in tasks.split(",") if item.strip()]
        if not task_list:
            return ForgeResult.failure("git.stack-plan", ["No tasks provided"], t.elapsed_ms, "Pass --tasks api,ui,docs")
        base_branch = base or _current_branch(cwd) or "main"
        branches = []
        previous = base_branch
        for idx, task in enumerate(task_list, start=1):
            branch = f"{prefix}/{idx:02d}-{task}"
            branches.append(
                {
                    "order": idx,
                    "task": task,
                    "branch": branch,
                    "base": previous,
                    "commands": [
                        f"git switch {previous}",
                        f"git switch -c {branch}",
                        "# implement task changes",
                        f"git push -u origin {branch}",
                        f"gh pr create --base {previous} --head {branch}",
                    ],
                }
            )
            previous = branch
        return ForgeResult.success(
            "git.stack-plan",
            {"base": base_branch, "prefix": prefix, "branches": branches, "note": "Plan only; no git commands were executed."},
            t.elapsed_ms,
        )


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--tasks", required=True, help="Comma-separated ordered task names")
    p.add_argument("--base", default="", help="Base branch, default current branch")
    p.add_argument("--prefix", default="stack", help="Branch prefix")


if __name__ == "__main__":
    make_cli("git.stack-plan", "Plan stacked PR branches from ordered task names", run, _args)
