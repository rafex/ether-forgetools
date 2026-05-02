"""forgetools.git.submodule_sync — Sync and update git submodules."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.submodule_sync"


def run(*, cwd: str | None = None, init: bool = True, recursive: bool = True) -> ForgeResult:
    with Timer() as t:
        # Step 1: git submodule sync
        sync_cmd = ["git", "submodule", "sync"]
        if recursive:
            sync_cmd.append("--recursive")
        try:
            rc, stdout, stderr = run_command(sync_cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["git not found"], suggestion="Install git")
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or "git submodule sync failed"],
                duration_ms=t.elapsed_ms,
                suggestion="Run inside a git repository",
            )

        # Step 2: git submodule update --init [--recursive]
        update_cmd = ["git", "submodule", "update"]
        if init:
            update_cmd.append("--init")
        if recursive:
            update_cmd.append("--recursive")
        try:
            rc2, stdout2, stderr2 = run_command(update_cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["git not found"], suggestion="Install git")
        if rc2 != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr2.strip() or "git submodule update failed"],
                duration_ms=t.elapsed_ms,
                suggestion="Check submodule URLs in .gitmodules",
            )

        combined = stdout + "\n" + stdout2 + "\n" + stderr2
        updated = _count_updated(combined)
        return ForgeResult.success(
            TOOL,
            {"synced": True, "init": init, "recursive": recursive, "submodules_updated": updated},
            t.elapsed_ms,
        )


def _count_updated(output: str) -> int:
    count = 0
    for line in output.splitlines():
        if "checked out" in line and "Submodule path" in line:
            count += 1
    return count


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--no-init", dest="init", action="store_false", default=True,
                   help="Skip --init flag on submodule update")
    p.add_argument("--no-recursive", dest="recursive", action="store_false", default=True,
                   help="Skip --recursive flag")


if __name__ == "__main__":
    make_cli(TOOL, "Sync and update git submodules", run, _add_args)
