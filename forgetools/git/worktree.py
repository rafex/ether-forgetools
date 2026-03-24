"""
Manage git worktrees: list, add, remove, move, prune, lock/unlock, status.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.worktree"

ACTIONS = ("list", "add", "remove", "move", "prune", "lock", "unlock", "status")


# ── parsers ───────────────────────────────────────────────────────────────────

def _parse_worktree_list(output: str) -> list[dict]:
    """Parse `git worktree list --porcelain` output into dicts."""
    worktrees: list[dict] = []
    current: dict = {}
    for line in output.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:], "branch": None, "sha": None,
                       "bare": False, "detached": False, "locked": False,
                       "locked_reason": None, "prunable": False}
        elif line.startswith("HEAD "):
            current["sha"] = line[5:]
        elif line.startswith("branch "):
            ref = line[7:]
            # refs/heads/main → main
            current["branch"] = ref.removeprefix("refs/heads/")
        elif line == "bare":
            current["bare"] = True
        elif line == "detached":
            current["detached"] = True
        elif line.startswith("locked"):
            current["locked"] = True
            if " " in line:
                current["locked_reason"] = line.split(" ", 1)[1]
        elif line.startswith("prunable"):
            current["prunable"] = True
    if current:
        worktrees.append(current)
    return worktrees


def _worktree_is_dirty(path: str) -> bool:
    try:
        rc, out, _ = run_command(
            ["git", "-C", path, "status", "--porcelain"],
            timeout=10,
        )
        return rc == 0 and bool(out.strip())
    except Exception:
        return False


# ── actions ───────────────────────────────────────────────────────────────────

def _list(cwd: str | None) -> ForgeResult:
    with Timer() as t:
        rc, out, err = run_command(["git", "worktree", "list", "--porcelain"], cwd=cwd)
        if rc != 0:
            return ForgeResult.failure(TOOL, [err.strip()], t.elapsed_ms,
                                       suggestion="Run inside a git repository")
        wts = _parse_worktree_list(out)
        return ForgeResult.success(TOOL, {
            "action": "list",
            "count": len(wts),
            "worktrees": wts,
        }, t.elapsed_ms)


def _status(cwd: str | None) -> ForgeResult:
    with Timer() as t:
        rc, out, err = run_command(["git", "worktree", "list", "--porcelain"], cwd=cwd)
        if rc != 0:
            return ForgeResult.failure(TOOL, [err.strip()], t.elapsed_ms)
        wts = _parse_worktree_list(out)
        for wt in wts:
            wt["dirty"] = _worktree_is_dirty(wt["path"])
        dirty_count = sum(1 for w in wts if w.get("dirty"))
        return ForgeResult.success(TOOL, {
            "action": "status",
            "count": len(wts),
            "dirty": dirty_count,
            "clean": len(wts) - dirty_count,
            "worktrees": wts,
        }, t.elapsed_ms)


def _add(path: str, branch: str | None, commit: str | None,
         new_branch: bool, cwd: str | None) -> ForgeResult:
    with Timer() as t:
        if not path:
            return ForgeResult.failure(TOOL, ["--path is required for add"], t.elapsed_ms)
        cmd = ["git", "worktree", "add"]
        if branch and new_branch:
            cmd += ["-b", branch]
        elif branch and not new_branch:
            # checkout existing branch
            pass
        cmd.append(path)
        if commit:
            cmd.append(commit)
        elif branch and not new_branch:
            cmd.append(branch)
        rc, out, err = run_command(cmd, cwd=cwd)
        if rc != 0:
            return ForgeResult.failure(TOOL, [err.strip()], t.elapsed_ms,
                                       suggestion="Use --new-branch to create a new branch")
        return ForgeResult.success(TOOL, {
            "action": "add",
            "path": str(Path(path).resolve()),
            "branch": branch,
            "commit": commit,
        }, t.elapsed_ms)


def _remove(path: str, force: bool, cwd: str | None) -> ForgeResult:
    with Timer() as t:
        if not path:
            return ForgeResult.failure(TOOL, ["--path is required for remove"], t.elapsed_ms)
        cmd = ["git", "worktree", "remove"]
        if force:
            cmd.append("--force")
        cmd.append(path)
        rc, out, err = run_command(cmd, cwd=cwd)
        if rc != 0:
            return ForgeResult.failure(TOOL, [err.strip()], t.elapsed_ms,
                                       suggestion="Use --force to remove a dirty worktree")
        return ForgeResult.success(TOOL, {"action": "remove", "path": path}, t.elapsed_ms)


def _move(path: str, new_path: str, cwd: str | None) -> ForgeResult:
    with Timer() as t:
        if not path or not new_path:
            return ForgeResult.failure(TOOL, ["--path and --new-path are required for move"], t.elapsed_ms)
        rc, out, err = run_command(["git", "worktree", "move", path, new_path],
                                   cwd=cwd)
        if rc != 0:
            return ForgeResult.failure(TOOL, [err.strip()], t.elapsed_ms)
        return ForgeResult.success(TOOL, {
            "action": "move", "from": path,
            "to": str(Path(new_path).resolve()),
        }, t.elapsed_ms)


def _prune(dry_run: bool, cwd: str | None) -> ForgeResult:
    with Timer() as t:
        cmd = ["git", "worktree", "prune", "--verbose"]
        if dry_run:
            cmd.append("--dry-run")
        rc, out, err = run_command(cmd, cwd=cwd)
        if rc != 0:
            return ForgeResult.failure(TOOL, [err.strip()], t.elapsed_ms)
        pruned = [l.strip() for l in (out + err).splitlines() if l.strip()]
        return ForgeResult.success(TOOL, {
            "action": "prune",
            "dry_run": dry_run,
            "pruned": pruned,
            "count": len(pruned),
        }, t.elapsed_ms)


def _lock(path: str, reason: str | None, unlock: bool, cwd: str | None) -> ForgeResult:
    with Timer() as t:
        if not path:
            return ForgeResult.failure(TOOL, ["--path is required for lock/unlock"], t.elapsed_ms)
        if unlock:
            cmd = ["git", "worktree", "unlock", path]
            action = "unlock"
        else:
            cmd = ["git", "worktree", "lock"]
            if reason:
                cmd += ["--reason", reason]
            cmd.append(path)
            action = "lock"
        rc, out, err = run_command(cmd, cwd=cwd)
        if rc != 0:
            return ForgeResult.failure(TOOL, [err.strip()], t.elapsed_ms)
        return ForgeResult.success(TOOL, {
            "action": action, "path": path, "reason": reason,
        }, t.elapsed_ms)


# ── public API ────────────────────────────────────────────────────────────────

def run(
    *,
    action: str = "list",
    path: str | None = None,
    new_path: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    new_branch: bool = False,
    force: bool = False,
    dry_run: bool = False,
    reason: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    match action:
        case "list":
            return _list(cwd)
        case "status":
            return _status(cwd)
        case "add":
            return _add(path or "", branch, commit, new_branch, cwd)
        case "remove":
            return _remove(path or "", force, cwd)
        case "move":
            return _move(path or "", new_path or "", cwd)
        case "prune":
            return _prune(dry_run, cwd)
        case "lock":
            return _lock(path or "", reason, unlock=False, cwd=cwd)
        case "unlock":
            return _lock(path or "", reason=None, unlock=True, cwd=cwd)
        case _:
            with Timer() as t:
                return ForgeResult.failure(
                    TOOL, [f"Unknown action: {action!r}"],
                    t.elapsed_ms,
                    suggestion=f"Valid actions: {', '.join(ACTIONS)}",
                )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=ACTIONS, help="Operation to perform")
    p.add_argument("--path",       help="Worktree path (add/remove/move/lock/unlock)")
    p.add_argument("--new-path",   dest="new_path", help="Destination path (move)")
    p.add_argument("--branch",     help="Branch name (add)")
    p.add_argument("--commit",     help="Commit-ish to checkout (add)")
    p.add_argument("--new-branch", dest="new_branch", action="store_true",
                   help="Create a new branch instead of checking out existing (add)")
    p.add_argument("--force",      action="store_true",
                   help="Force removal of dirty worktree (remove)")
    p.add_argument("--dry-run",    dest="dry_run", action="store_true",
                   help="Show what would be pruned without deleting (prune)")
    p.add_argument("--reason",     help="Lock reason message (lock)")


if __name__ == "__main__":
    make_cli(TOOL, "Manage git worktrees", run, _add_args)
