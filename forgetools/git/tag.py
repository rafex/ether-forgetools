"""forgetools.git.tag — List, create, or delete git tags."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.tag"

_VALID_ACTIONS = ("list", "create", "delete")


def run(
    *,
    action: str = "list",
    name: str | None = None,
    message: str | None = None,
    ref: str = "HEAD",
    push: bool = False,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if action not in _VALID_ACTIONS:
            return ForgeResult.failure(
                TOOL,
                [f"Invalid action: {action}. Choose from: {', '.join(_VALID_ACTIONS)}"],
                duration_ms=t.elapsed_ms,
            )
        try:
            if action == "list":
                return _list_tags(cwd, t)
            elif action == "create":
                if not name:
                    return ForgeResult.failure(TOOL, ["--name required for create"], duration_ms=t.elapsed_ms)
                return _create_tag(name, message, ref, push, cwd, t)
            else:
                if not name:
                    return ForgeResult.failure(TOOL, ["--name required for delete"], duration_ms=t.elapsed_ms)
                return _delete_tag(name, push, cwd, t)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["git not found"], suggestion="Install git")


def _list_tags(cwd: str | None, t) -> ForgeResult:
    rc, stdout, stderr = run_command(
        ["git", "for-each-ref", "--sort=-version:refname",
         "--format=%(refname:short) %(objectname:short) %(creatordate:short)",
         "refs/tags"],
        cwd=cwd,
    )
    if rc != 0:
        return ForgeResult.failure(TOOL, [stderr.strip() or "git for-each-ref failed"], duration_ms=t.elapsed_ms)
    tags = []
    for line in stdout.strip().splitlines():
        parts = line.split(" ", 2)
        tags.append({"name": parts[0], "sha": parts[1] if len(parts) > 1 else ""})
    return ForgeResult.success(TOOL, {"tags": tags}, t.elapsed_ms)


def _create_tag(name: str, message: str | None, ref: str, push: bool, cwd: str | None, t) -> ForgeResult:
    if message:
        cmd = ["git", "tag", "-a", "-m", message, name, ref]
    else:
        cmd = ["git", "tag", name, ref]
    rc, stdout, stderr = run_command(cmd, cwd=cwd)
    if rc != 0:
        return ForgeResult.failure(TOOL, [stderr.strip() or "git tag create failed"], duration_ms=t.elapsed_ms)
    pushed = False
    if push:
        rc2, _, stderr2 = run_command(["git", "push", "origin", name], cwd=cwd)
        pushed = rc2 == 0
        if not pushed:
            return ForgeResult.failure(
                TOOL, [stderr2.strip() or "git push tag failed"],
                duration_ms=t.elapsed_ms, suggestion="Check remote access"
            )
    return ForgeResult.success(TOOL, {"action": "create", "name": name, "pushed": pushed}, t.elapsed_ms)


def _delete_tag(name: str, push: bool, cwd: str | None, t) -> ForgeResult:
    rc, _, stderr = run_command(["git", "tag", "-d", name], cwd=cwd)
    if rc != 0:
        return ForgeResult.failure(TOOL, [stderr.strip() or "git tag delete failed"], duration_ms=t.elapsed_ms)
    pushed = False
    if push:
        rc2, _, stderr2 = run_command(["git", "push", "origin", "--delete", name], cwd=cwd)
        pushed = rc2 == 0
        if not pushed:
            return ForgeResult.failure(
                TOOL, [stderr2.strip() or "git push delete tag failed"],
                duration_ms=t.elapsed_ms, suggestion="Check remote access"
            )
    return ForgeResult.success(TOOL, {"action": "delete", "name": name, "pushed": pushed}, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="list", choices=list(_VALID_ACTIONS))
    p.add_argument("--name", default=None, help="Tag name (required for create/delete)")
    p.add_argument("--message", default=None, help="Annotated tag message")
    p.add_argument("--ref", default="HEAD", help="Ref to tag (default: HEAD)")
    p.add_argument("--push", action="store_true", default=False, help="Push tag to origin")


if __name__ == "__main__":
    make_cli(TOOL, "List, create, or delete git tags", run, _add_args)
