"""forgetools.git.worktree_merge_plan - Plan integration and merge readiness for worktree sessions."""
from __future__ import annotations

import argparse
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command


def _git(args: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    return run_command(["git", *args], cwd=cwd, timeout=20)


def _parse_worktrees(output: str) -> list[dict]:
    worktrees: list[dict] = []
    current: dict = {}
    for line in output.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:], "branch": None, "sha": None}
        elif line.startswith("HEAD "):
            current["sha"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:].removeprefix("refs/heads/")
    if current:
        worktrees.append(current)
    return worktrees


def _dirty(path: str) -> tuple[bool, str]:
    rc, out, err = run_command(["git", "-C", path, "status", "--porcelain"], timeout=10)
    if rc != 0:
        return True, err.strip()
    return bool(out.strip()), out.strip()


def _ahead_behind(path: str, upstream: str) -> tuple[int, int, str | None]:
    rc, out, err = run_command(["git", "-C", path, "rev-list", "--left-right", "--count", f"{upstream}...HEAD"], timeout=10)
    if rc != 0:
        return 0, 0, err.strip()
    parts = out.strip().split()
    if len(parts) != 2:
        return 0, 0, None
    return int(parts[1]), int(parts[0]), None


def _commits_between(branch: str, target: str, cwd: str | None) -> list[str]:
    rc, out, _ = _git(["log", "--oneline", f"{target}..{branch}"], cwd=cwd)
    return out.splitlines() if rc == 0 and out.strip() else []


def run(
    *,
    session: str,
    base_branch: str = "main",
    branch_prefix: str = "ai",
    target_branch: str = "",
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        rc, out, err = _git(["worktree", "list", "--porcelain"], cwd=cwd)
        if rc != 0:
            return ForgeResult.failure("git.worktree-merge-plan", [err.strip()], t.elapsed_ms, "Run inside a git repository.")

        target = target_branch or base_branch
        integration_branch = f"{branch_prefix}/{session}-integration"
        all_wts = _parse_worktrees(out)
        session_wts = [
            wt for wt in all_wts
            if wt.get("branch") == integration_branch
            or (wt.get("branch") or "").startswith(f"{branch_prefix}/{session}-")
        ]

        if not session_wts:
            return ForgeResult.failure(
                "git.worktree-merge-plan",
                [f"No worktrees found for session '{session}' with prefix '{branch_prefix}'"],
                t.elapsed_ms,
                "Run git_worktree_workflow(action='init') first or verify --session/--branch-prefix.",
            )

        tasks = []
        integration = None
        risks = []
        for wt in session_wts:
            branch = wt.get("branch") or ""
            is_integration = branch == integration_branch
            is_dirty, dirty_detail = _dirty(wt["path"]) if Path(wt["path"]).exists() else (True, "missing path")
            if is_dirty:
                risks.append({"branch": branch, "risk": "dirty_worktree", "detail": dirty_detail})

            if is_integration:
                ahead, behind, ab_error = _ahead_behind(wt["path"], target)
                integration = {
                    **wt,
                    "dirty": is_dirty,
                    "ahead_of_target": ahead,
                    "behind_target": behind,
                    "ahead_behind_error": ab_error,
                }
                continue

            task = branch.removeprefix(f"{branch_prefix}/{session}-")
            ahead, behind, ab_error = _ahead_behind(wt["path"], integration_branch)
            commits = _commits_between(branch, integration_branch, cwd)
            ready = not is_dirty and bool(commits)
            tasks.append(
                {
                    **wt,
                    "task": task,
                    "dirty": is_dirty,
                    "ahead_of_integration": ahead,
                    "behind_integration": behind,
                    "ahead_behind_error": ab_error,
                    "commits_to_integrate": commits,
                    "ready_to_integrate": ready,
                }
            )
            if behind:
                risks.append({"branch": branch, "risk": "behind_integration", "detail": f"{behind} commits behind {integration_branch}"})

        commands = [
            f"forge git worktree-workflow --action status --session {session} --base-branch {base_branch} --branch-prefix {branch_prefix}",
            f"forge git worktree-workflow --action sync --session {session} --base-branch {base_branch} --branch-prefix {branch_prefix}",
        ]
        commands.extend(
            f"forge git worktree-workflow --action integrate --session {session} --task {task['task']} --branch-prefix {branch_prefix}"
            for task in tasks
            if task["ready_to_integrate"]
        )
        commands.append(
            f"forge git worktree-workflow --action finalize --session {session} --target-branch {target} --branch-prefix {branch_prefix}"
        )

        return ForgeResult.success(
            "git.worktree-merge-plan",
            {
                "session": session,
                "base_branch": base_branch,
                "target_branch": target,
                "integration_branch": integration_branch,
                "integration": integration,
                "tasks": tasks,
                "ready_to_integrate": [task["task"] for task in tasks if task["ready_to_integrate"]],
                "blocked": [task["task"] for task in tasks if not task["ready_to_integrate"]],
                "risks": risks,
                "recommended_commands": commands,
                "note": "Plan only; no git changes were made.",
            },
            t.elapsed_ms,
        )


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--session", required=True, help="Worktree workflow session name")
    p.add_argument("--base-branch", default="main", help="Base branch")
    p.add_argument("--branch-prefix", default="ai", help="Session branch prefix")
    p.add_argument("--target-branch", default="", help="Merge target branch, default base branch")


if __name__ == "__main__":
    make_cli("git.worktree-merge-plan", "Plan integration and merge readiness for worktree sessions", run, _args)
