from __future__ import annotations

"""
git/worktree_workflow.py — Parallel worktree workflow engine for AI agents.

A "session" is a named set of git worktrees where an AI agent performs
independent tasks simultaneously, then merges all changes through an
integration branch before landing on main (or any target branch).

Workflow:

  1. plan       — preview: branch names, paths, order of operations (no writes)
  2. init       — create integration branch + one worktree per task
  3. status     — dirty/clean + ahead-behind for every worktree in the session
  4. sync       — rebase/merge every task worktree from base_branch
  5. integrate  — merge completed task branches → integration branch (one or all)
  6. finalize   — merge integration → target branch; optionally remove worktrees
  7. abort      — remove all session worktrees + delete task/integration branches

Session naming convention (all derived from `session`):
  integration branch : {branch_prefix}/{session}-integration
  per-task branches  : {branch_prefix}/{session}-{task}
  worktree paths     : {worktree_base}/{session}-{task}

The session is stateless — `status` / `integrate` / `finalize` / `abort` all
re-derive the session topology from the running worktree list + branch names.
"""

import argparse
import json
import os
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.worktree_workflow"

ACTIONS = ("plan", "init", "status", "sync", "integrate", "finalize", "abort")

_DEFAULT_PREFIX      = "ai"          # branch prefix: ai/<session>-...
_DEFAULT_WT_BASE     = "../.claude/worktrees"
_DEFAULT_MERGE       = "merge"


# ── git helpers ───────────────────────────────────────────────────────────────

def _git(args: list[str], cwd: str | None = None, timeout: int = 20) -> tuple[int, str, str]:
    return run_command(["git"] + args, cwd=cwd, timeout=timeout)


def _current_branch(cwd: str | None) -> str:
    _, out, _ = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return out.strip()


def _repo_root(cwd: str | None) -> str:
    _, out, _ = _git(["rev-parse", "--show-toplevel"], cwd=cwd)
    return out.strip()


def _branch_exists(branch: str, cwd: str | None) -> bool:
    rc, _, _ = _git(["rev-parse", "--verify", branch], cwd=cwd)
    return rc == 0


def _worktree_list(cwd: str | None) -> list[dict]:
    rc, out, _ = _git(["worktree", "list", "--porcelain"], cwd=cwd)
    if rc != 0:
        return []
    wts: list[dict] = []
    cur: dict = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            if cur:
                wts.append(cur)
            cur = {"path": line[9:], "branch": None, "sha": None,
                   "bare": False, "detached": False, "locked": False}
        elif line.startswith("HEAD "):
            cur["sha"] = line[5:]
        elif line.startswith("branch "):
            cur["branch"] = line[7:].removeprefix("refs/heads/")
        elif line == "bare":
            cur["bare"] = True
        elif line == "detached":
            cur["detached"] = True
        elif line.startswith("locked"):
            cur["locked"] = True
    if cur:
        wts.append(cur)
    return wts


def _is_dirty(path: str) -> bool:
    rc, out, _ = run_command(["git", "-C", path, "status", "--porcelain"], timeout=10)
    return rc == 0 and bool(out.strip())


def _ahead_behind(path: str, upstream: str) -> tuple[int, int]:
    """Return (ahead, behind) relative to `upstream` in worktree at `path`."""
    rc, out, _ = run_command(
        ["git", "-C", path, "rev-list", "--left-right", "--count",
         f"{upstream}...HEAD"],
        timeout=10,
    )
    if rc != 0 or not out.strip():
        return 0, 0
    parts = out.strip().split()
    if len(parts) == 2:
        return int(parts[1]), int(parts[0])   # ahead, behind
    return 0, 0


def _has_commits_not_in(branch: str, target: str, cwd: str | None) -> bool:
    """True if branch has commits not yet in target."""
    rc, out, _ = _git(
        ["log", "--oneline", f"{target}..{branch}", "--"],
        cwd=cwd, timeout=10,
    )
    return rc == 0 and bool(out.strip())


# ── session topology ─────────────────────────────────────────────────────────

def _integration_branch(session: str, prefix: str) -> str:
    return f"{prefix}/{session}-integration"


def _task_branch(session: str, task: str, prefix: str) -> str:
    return f"{prefix}/{session}-{task}"


def _task_wt_path(session: str, task: str, wt_base: str, repo_root: str) -> str:
    base = Path(wt_base) if Path(wt_base).is_absolute() else Path(repo_root) / wt_base
    return str(base.resolve() / f"{session}-{task}")


def _session_topology(
    session: str, tasks: list[str], prefix: str, wt_base: str, repo_root: str,
) -> dict:
    """Derive all branch/path names for a session without touching git."""
    int_branch = _integration_branch(session, prefix)
    task_entries = [
        {
            "task":    task,
            "branch":  _task_branch(session, task, prefix),
            "path":    _task_wt_path(session, task, wt_base, repo_root),
        }
        for task in tasks
    ]
    return {
        "session":              session,
        "integration_branch":   int_branch,
        "tasks":                task_entries,
        "worktree_count":       len(task_entries),
    }


def _detect_session_worktrees(
    session: str, prefix: str, all_wts: list[dict],
) -> list[dict]:
    """Find worktrees that belong to this session (by branch naming convention)."""
    int_branch = _integration_branch(session, prefix)
    result = []
    for wt in all_wts:
        br = wt.get("branch") or ""
        if br == int_branch:
            result.append({**wt, "role": "integration"})
        elif br.startswith(f"{prefix}/{session}-") and br != int_branch:
            task = br.removeprefix(f"{prefix}/{session}-")
            result.append({**wt, "role": "task", "task": task})
    return result


# ── actions ───────────────────────────────────────────────────────────────────

def _plan(
    session: str, tasks: list[str], base_branch: str, prefix: str,
    wt_base: str, cwd: str | None,
) -> dict:
    root    = _repo_root(cwd) or (cwd or os.getcwd())
    topo    = _session_topology(session, tasks, prefix, wt_base, root)
    int_br  = topo["integration_branch"]

    all_wts = _worktree_list(cwd)
    existing_branches = {wt.get("branch") for wt in all_wts}

    steps = [
        f"1. Create integration branch `{int_br}` from `{base_branch}`",
    ]
    for idx, entry in enumerate(topo["tasks"], 2):
        br   = entry["branch"]
        path = entry["path"]
        task = entry["task"]
        steps.append(
            f"{idx}. Create worktree `{path}` on branch `{br}` "
            f"(task: {task})"
        )
    merge_step = len(topo["tasks"]) + 2
    steps.append(
        f"{merge_step}. After completing each task, run "
        f"`integrate` to merge into `{int_br}`"
    )
    steps.append(
        f"{merge_step + 1}. Run `finalize` to merge `{int_br}` → `{base_branch}` "
        f"and remove worktrees"
    )

    return {
        "preview":            True,
        "session":            session,
        "base_branch":        base_branch,
        "integration_branch": int_br,
        "tasks":              topo["tasks"],
        "worktree_count":     len(tasks),
        "steps":              steps,
        "conflicts": [
            entry for entry in topo["tasks"]
            if entry["branch"] in existing_branches or Path(entry["path"]).exists()
        ],
        "agent_tip": (
            "Run `init` to create all worktrees.  "
            "Work on each task in its worktree path.  "
            "Call `integrate` (with --task) as each task is completed.  "
            "Call `finalize` once all tasks are integrated."
        ),
    }


def _init(
    session: str, tasks: list[str], base_branch: str, prefix: str,
    wt_base: str, cwd: str | None,
) -> dict:
    if not tasks:
        raise ValueError("--tasks is required for init")

    root   = _repo_root(cwd) or (cwd or os.getcwd())
    topo   = _session_topology(session, tasks, prefix, wt_base, root)
    int_br = topo["integration_branch"]

    created = []
    errors  = []

    # 1. Create integration branch
    if _branch_exists(int_br, cwd):
        errors.append(f"Integration branch '{int_br}' already exists; skipping creation")
    else:
        rc, _, err = _git(["checkout", "-b", int_br, base_branch], cwd=cwd)
        if rc != 0:
            raise RuntimeError(f"Failed to create integration branch: {err.strip()}")
        created.append({"type": "branch", "name": int_br})
        # return to original branch immediately (or base_branch)
        _git(["checkout", base_branch], cwd=cwd)

    # 2. Create per-task worktrees
    for entry in topo["tasks"]:
        task   = entry["task"]
        branch = entry["branch"]
        path   = entry["path"]

        if Path(path).exists():
            errors.append(f"Worktree path '{path}' already exists; skipping task '{task}'")
            continue

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        if _branch_exists(branch, cwd):
            # checkout existing branch in new worktree
            rc, _, err = _git(["worktree", "add", path, branch], cwd=cwd)
        else:
            # create new branch from base_branch in worktree
            rc, _, err = _git(
                ["worktree", "add", "-b", branch, path, base_branch], cwd=cwd
            )

        if rc != 0:
            errors.append(f"Failed to create worktree for task '{task}': {err.strip()}")
            continue

        created.append({"type": "worktree", "task": task, "branch": branch, "path": path})

    return {
        "session":            session,
        "base_branch":        base_branch,
        "integration_branch": int_br,
        "created":            created,
        "errors":             errors,
        "tasks":              topo["tasks"],
        "next_step": (
            f"Work independently in each worktree path. "
            f"When a task is done, call `integrate --task <name>` "
            f"to merge it into `{int_br}`."
        ),
    }


def _status(
    session: str, prefix: str, base_branch: str, cwd: str | None,
) -> dict:
    all_wts = _worktree_list(cwd)
    session_wts = _detect_session_worktrees(session, prefix, all_wts)

    if not session_wts:
        return {
            "session":     session,
            "found":       False,
            "message":     f"No worktrees found for session '{session}' "
                           f"(prefix: {prefix}). Run `init` first.",
        }

    int_branch = _integration_branch(session, prefix)
    enriched = []
    for wt in session_wts:
        path   = wt["path"]
        branch = wt.get("branch", "")
        dirty  = _is_dirty(path) if Path(path).exists() else False

        # ahead/behind vs integration branch
        ahead, behind = 0, 0
        if _branch_exists(int_branch, cwd) and wt["role"] == "task":
            ahead, behind = _ahead_behind(path, int_branch)

        # ahead/behind vs base_branch for integration
        ab_base = {}
        if wt["role"] == "integration" and _branch_exists(base_branch, cwd):
            ahead_b, behind_b = _ahead_behind(path, base_branch)
            ab_base = {"ahead_of_base": ahead_b, "behind_base": behind_b}

        enriched.append({
            **wt,
            "dirty":          dirty,
            "ahead_of_int":   ahead if wt["role"] == "task" else None,
            "behind_int":     behind if wt["role"] == "task" else None,
            **ab_base,
        })

    tasks_done = [
        w for w in enriched
        if w["role"] == "task" and not w["dirty"] and w.get("ahead_of_int", 0) > 0
    ]
    tasks_pending = [w for w in enriched if w["role"] == "task" and w["dirty"]]

    return {
        "session":            session,
        "found":              True,
        "integration_branch": int_branch,
        "worktree_count":     len(session_wts),
        "ready_to_integrate": [w["task"] for w in tasks_done],
        "in_progress":        [w["task"] for w in tasks_pending],
        "worktrees":          enriched,
    }


def _sync(
    session: str, prefix: str, base_branch: str, merge_method: str, cwd: str | None,
) -> dict:
    """Pull latest from base_branch into every task worktree."""
    all_wts = _worktree_list(cwd)
    session_wts = _detect_session_worktrees(session, prefix, all_wts)
    task_wts    = [w for w in session_wts if w["role"] == "task"]

    if not task_wts:
        return {"session": session, "synced": [], "message": "No task worktrees found"}

    synced = []
    errors = []

    # fetch latest
    _git(["fetch", "origin", base_branch], cwd=cwd, timeout=30)

    for wt in task_wts:
        path = wt["path"]
        task = wt.get("task", "?")
        if not Path(path).exists():
            errors.append(f"Worktree path '{path}' not found")
            continue

        if merge_method == "rebase":
            rc, out, err = run_command(
                ["git", "-C", path, "rebase", base_branch], timeout=30
            )
        else:
            rc, out, err = run_command(
                ["git", "-C", path, "merge", base_branch], timeout=30
            )

        if rc != 0:
            errors.append(f"Sync failed for task '{task}': {err.strip()}")
        else:
            synced.append({"task": task, "path": path, "method": merge_method})

    return {
        "session":    session,
        "method":     merge_method,
        "base_branch": base_branch,
        "synced":     synced,
        "errors":     errors,
    }


def _integrate(
    session: str, task: str | None, prefix: str, merge_method: str, cwd: str | None,
) -> dict:
    """Merge one or all completed task branches into the integration branch."""
    int_branch = _integration_branch(session, prefix)
    if not _branch_exists(int_branch, cwd):
        raise RuntimeError(
            f"Integration branch '{int_branch}' not found. Run `init` first."
        )

    all_wts     = _worktree_list(cwd)
    session_wts = _detect_session_worktrees(session, prefix, all_wts)
    task_wts    = [w for w in session_wts if w["role"] == "task"]

    # filter to specific task if requested
    if task:
        task_wts = [w for w in task_wts if w.get("task") == task]
        if not task_wts:
            raise ValueError(
                f"Task '{task}' not found in session '{session}'. "
                f"Available: {[w.get('task') for w in task_wts]}"
            )

    # find the integration worktree (or use cwd)
    int_wts = [w for w in session_wts if w["role"] == "integration"]
    int_path = int_wts[0]["path"] if int_wts else None

    merged = []
    errors = []
    skipped = []

    for wt in task_wts:
        task_name   = wt.get("task", "?")
        task_branch = wt.get("branch", "")

        if not _has_commits_not_in(task_branch, int_branch, cwd):
            skipped.append({"task": task_name, "reason": "no new commits vs integration"})
            continue

        if merge_method == "squash":
            cmd = ["git", "merge", "--squash", task_branch]
        elif merge_method == "rebase":
            # rebase task onto integration and then fast-forward
            # (simpler: just merge from integration worktree)
            cmd = ["git", "merge", "--no-ff", task_branch,
                   "-m", f"integrate: merge task '{task_name}' from {task_branch}"]
        else:
            cmd = ["git", "merge", "--no-ff", task_branch,
                   "-m", f"integrate: merge task '{task_name}' from {task_branch}"]

        if int_path and Path(int_path).exists():
            rc, out, err = run_command(["git", "-C", int_path] + cmd[1:], timeout=30)
        else:
            # checkout integration branch and merge
            rc, _, err0 = _git(["checkout", int_branch], cwd=cwd)
            if rc != 0:
                errors.append(f"Could not checkout {int_branch}: {err0.strip()}")
                continue
            rc, out, err = _git(cmd[1:], cwd=cwd)
            # restore caller's branch
            _git(["checkout", "-"], cwd=cwd)

        if rc != 0:
            errors.append(f"Merge failed for task '{task_name}': {err.strip()}")
        else:
            if merge_method == "squash":
                # squash merge leaves changes staged — commit them
                _rc, _o, _e = (
                    run_command(
                        ["git", "-C", int_path or (cwd or "."),
                         "commit", "-m",
                         f"integrate: squash task '{task_name}' from {task_branch}"],
                        timeout=15,
                    )
                    if int_path and Path(int_path).exists()
                    else _git(
                        ["commit", "-m",
                         f"integrate: squash task '{task_name}' from {task_branch}"],
                        cwd=cwd,
                    )
                )
            merged.append({"task": task_name, "branch": task_branch, "method": merge_method})

    return {
        "session":            session,
        "integration_branch": int_branch,
        "method":             merge_method,
        "merged":             merged,
        "skipped":            skipped,
        "errors":             errors,
        "next_step": (
            "When all tasks are integrated, call `finalize` to merge "
            f"`{int_branch}` into the target branch and clean up."
        ) if not errors else "Fix merge conflicts in the listed tasks, then re-run integrate.",
    }


def _finalize(
    session: str, prefix: str, target_branch: str, merge_method: str,
    cleanup: bool, cwd: str | None,
) -> dict:
    """Merge integration branch → target_branch, optionally remove worktrees."""
    int_branch = _integration_branch(session, prefix)
    if not _branch_exists(int_branch, cwd):
        raise RuntimeError(f"Integration branch '{int_branch}' not found.")

    # Check integration has commits not in target
    if not _has_commits_not_in(int_branch, target_branch, cwd):
        return {
            "session":            session,
            "integration_branch": int_branch,
            "target_branch":      target_branch,
            "merged":             False,
            "message":            f"No new commits in '{int_branch}' vs '{target_branch}'",
        }

    # Checkout target and merge
    rc, _, err = _git(["checkout", target_branch], cwd=cwd)
    if rc != 0:
        raise RuntimeError(f"Could not checkout '{target_branch}': {err.strip()}")

    if merge_method == "squash":
        merge_cmd = ["merge", "--squash", int_branch]
    else:
        merge_cmd = ["merge", "--no-ff", int_branch,
                     "-m", f"feat: merge session '{session}' from {int_branch}"]

    rc, out, err = _git(merge_cmd, cwd=cwd)
    if rc != 0:
        raise RuntimeError(f"Merge failed: {err.strip()}")

    if merge_method == "squash":
        _git(["commit", "-m", f"feat: squash-merge session '{session}'"], cwd=cwd)

    removed = []
    if cleanup:
        all_wts     = _worktree_list(cwd)
        session_wts = _detect_session_worktrees(session, prefix, all_wts)
        # remove task worktrees (not integration — that is a branch, not necessarily a WT)
        for wt in session_wts:
            if wt["role"] == "task":
                rm_rc, _, rm_err = _git(
                    ["worktree", "remove", "--force", wt["path"]], cwd=cwd
                )
                if rm_rc == 0:
                    removed.append(wt["path"])
                    # delete task branch
                    _git(["branch", "-d", wt["branch"]], cwd=cwd)
                else:
                    removed.append(f"FAILED {wt['path']}: {rm_err.strip()}")
        # prune stale entries
        _git(["worktree", "prune"], cwd=cwd)
        # delete integration branch
        _git(["branch", "-d", int_branch], cwd=cwd)

    return {
        "session":            session,
        "integration_branch": int_branch,
        "target_branch":      target_branch,
        "method":             merge_method,
        "merged":             True,
        "cleanup":            cleanup,
        "removed_worktrees":  removed,
        "next_step": (
            "Session complete. Push the target branch: git push origin "
            + target_branch
        ),
    }


def _abort(
    session: str, prefix: str, cwd: str | None,
) -> dict:
    """Remove all session worktrees and delete task + integration branches."""
    all_wts     = _worktree_list(cwd)
    session_wts = _detect_session_worktrees(session, prefix, all_wts)
    int_branch  = _integration_branch(session, prefix)

    removed = []
    deleted_branches = []
    errors  = []

    for wt in session_wts:
        path   = wt["path"]
        branch = wt.get("branch", "")
        rc, _, err = _git(["worktree", "remove", "--force", path], cwd=cwd)
        if rc == 0:
            removed.append(path)
        else:
            errors.append(f"Could not remove {path}: {err.strip()}")
        if branch and branch != _current_branch(cwd):
            br_rc, _, _ = _git(["branch", "-D", branch], cwd=cwd)
            if br_rc == 0:
                deleted_branches.append(branch)

    _git(["worktree", "prune"], cwd=cwd)

    # delete integration branch if it still exists
    if _branch_exists(int_branch, cwd):
        br_rc, _, _ = _git(["branch", "-D", int_branch], cwd=cwd)
        if br_rc == 0:
            deleted_branches.append(int_branch)

    return {
        "session":          session,
        "aborted":          True,
        "removed_worktrees": removed,
        "deleted_branches": deleted_branches,
        "errors":           errors,
    }


# ── public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action:           str       = "status",
    session:          str       = "",
    tasks:            list[str] | None = None,
    task:             str | None = None,
    base_branch:      str       = "main",
    target_branch:    str | None = None,
    branch_prefix:    str       = _DEFAULT_PREFIX,
    worktree_base:    str       = _DEFAULT_WT_BASE,
    merge_method:     str       = _DEFAULT_MERGE,
    cleanup:          bool      = True,
    cwd:              str | None = None,
) -> ForgeResult:
    with Timer() as t:
        try:
            if not session:
                return ForgeResult.failure(
                    TOOL,
                    ["--session is required (a short name identifying the parallel work, e.g. 'auth-refactor')"],
                    t.elapsed_ms,
                )

            _tasks  = tasks or []
            _target = target_branch or base_branch

            if action == "plan":
                if not _tasks:
                    return ForgeResult.failure(
                        TOOL, ["--tasks is required for plan"], t.elapsed_ms
                    )
                data = _plan(session, _tasks, base_branch, branch_prefix, worktree_base, cwd)

            elif action == "init":
                if not _tasks:
                    return ForgeResult.failure(
                        TOOL, ["--tasks is required for init"], t.elapsed_ms
                    )
                data = _init(session, _tasks, base_branch, branch_prefix, worktree_base, cwd)

            elif action == "status":
                data = _status(session, branch_prefix, base_branch, cwd)

            elif action == "sync":
                data = _sync(session, branch_prefix, base_branch, merge_method, cwd)

            elif action == "integrate":
                data = _integrate(session, task, branch_prefix, merge_method, cwd)

            elif action == "finalize":
                data = _finalize(session, branch_prefix, _target, merge_method, cleanup, cwd)

            elif action == "abort":
                data = _abort(session, branch_prefix, cwd)

            else:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unknown action '{action}'. Valid: {', '.join(ACTIONS)}"],
                    t.elapsed_ms,
                )

        except Exception as exc:
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action",        default="status", choices=ACTIONS)
    p.add_argument("--session",       required=True,
                   help="Session name — short slug identifying the parallel work")
    p.add_argument("--tasks",         nargs="+", default=None,
                   help="Task names (required for plan/init)")
    p.add_argument("--task",          default=None,
                   help="Single task name (for integrate)")
    p.add_argument("--base-branch",   dest="base_branch",   default="main",
                   help="Branch to branch off (default: main)")
    p.add_argument("--target-branch", dest="target_branch", default=None,
                   help="Branch to merge into at finalize (default: base_branch)")
    p.add_argument("--branch-prefix", dest="branch_prefix", default=_DEFAULT_PREFIX,
                   help=f"Prefix for all session branches (default: {_DEFAULT_PREFIX!r})")
    p.add_argument("--worktree-base", dest="worktree_base", default=_DEFAULT_WT_BASE,
                   help=f"Parent directory for worktrees (default: {_DEFAULT_WT_BASE!r})")
    p.add_argument("--merge-method",  dest="merge_method",  default=_DEFAULT_MERGE,
                   choices=["merge", "squash", "rebase"],
                   help="How to integrate commits (default: merge)")
    p.add_argument("--no-cleanup",    dest="cleanup", action="store_false",
                   help="Do NOT remove worktrees after finalize")


if __name__ == "__main__":
    make_cli(
        TOOL,
        "Parallel worktree workflow for AI agents: plan/init/status/sync/integrate/finalize/abort",
        run, _add_args,
    )
