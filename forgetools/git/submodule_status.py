"""forgetools.git.submodule_status — Git submodule status."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.submodule_status"

_STATE_MAP = {
    " ": "clean",
    "-": "uninitialized",
    "+": "modified",
    "U": "conflict",
}


def run(*, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            rc, stdout, stderr = run_command(
                ["git", "submodule", "status"], cwd=cwd
            )
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["git not found"], suggestion="Install git")
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or "git submodule status failed"],
                duration_ms=t.elapsed_ms,
                suggestion="Run inside a git repository",
            )
        return ForgeResult.success(TOOL, _parse(stdout), t.elapsed_ms)


def _parse(output: str) -> dict:
    submodules = []
    clean = modified = uninitialized = conflict = 0

    for line in output.splitlines():
        if not line:
            continue
        prefix = line[0]
        rest = line[1:]
        state = _STATE_MAP.get(prefix, "clean")

        # format: <sha> <path> (<description>)
        parts = rest.split(" ", 2)
        sha = parts[0] if len(parts) > 0 else ""
        path = parts[1] if len(parts) > 1 else ""
        description: str | None = None
        if len(parts) > 2:
            desc = parts[2].strip()
            if desc.startswith("(") and desc.endswith(")"):
                description = desc[1:-1]
            else:
                description = desc or None

        submodules.append({"path": path, "sha": sha, "state": state, "description": description})
        if state == "clean":
            clean += 1
        elif state == "modified":
            modified += 1
        elif state == "uninitialized":
            uninitialized += 1
        elif state == "conflict":
            conflict += 1

    return {
        "total": len(submodules),
        "clean": clean,
        "modified": modified,
        "uninitialized": uninitialized,
        "conflict": conflict,
        "submodules": submodules,
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    pass


if __name__ == "__main__":
    make_cli(TOOL, "Show git submodule status", run, _add_args)
