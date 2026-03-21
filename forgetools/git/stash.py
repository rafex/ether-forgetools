"""forgetools.git.stash — List and manage git stashes."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "git.stash"


def run(*, cwd: str | None = None, action: str = "list", message: str | None = None) -> ForgeResult:
    if action == "list":
        cmd = ["git", "stash", "list", "--pretty=format:%gd|%s|%ci"]
        return run_and_build(cmd, tool_name=TOOL, cwd=cwd, data_fn=_parse_list)
    elif action == "save":
        cmd = ["git", "stash", "push", "-m", message or "forgetools stash"]
        return run_and_build(cmd, tool_name=TOOL, cwd=cwd, data_fn=lambda o, _: {"message": o.strip()})
    elif action in ("pop", "apply", "drop"):
        cmd = ["git", "stash", action]
        return run_and_build(cmd, tool_name=TOOL, cwd=cwd, data_fn=lambda o, _: {"output": o.strip()})
    else:
        return ForgeResult.failure(TOOL, [f"Unknown action: {action}"], suggestion="Use: list, save, pop, apply, drop")


def _parse_list(stdout: str, _stderr: str) -> list[dict]:
    result = []
    for line in stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            result.append({"ref": parts[0], "message": parts[1], "date": parts[2]})
    return result


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="list", choices=["list", "save", "pop", "apply", "drop"])
    p.add_argument("--message", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Manage git stashes", run, _add_args)
