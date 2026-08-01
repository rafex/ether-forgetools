"""Operational git actions with preview-by-default safety semantics."""
from __future__ import annotations

import argparse
import shlex

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.operations"
READ_ACTIONS = {"remote", "show", "reflog"}
MUTATING_ACTIONS = {
    "fetch", "pull", "push", "switch", "restore", "merge", "rebase", "reset", "clean",
    "revert", "bisect", "branch-create", "branch-delete", "remote-add", "remote-remove",
    "remote-set-url", "remote-prune", "maintenance",
}
ACTIONS = tuple(sorted(READ_ACTIONS | MUTATING_ACTIONS))


def run(
    *,
    action: str = "remote",
    cwd: str | None = None,
    execute: bool = False,
    confirm: bool = False,
    remote: str = "origin",
    remote_url: str = "",
    branch: str = "",
    ref: str = "",
    path: str = "",
    paths: str = "",
    staged: bool = False,
    create: bool = False,
    rebase: bool = False,
    ff_only: bool = True,
    source: str = "",
    reset_mode: str = "mixed",
    prune: bool = False,
    include_dirs: bool = False,
    force_with_lease: bool = False,
    patch: bool = False,
    max_lines: int = 200,
    count: int = 20,
    rebase_action: str = "",
    bisect_action: str = "",
    maintenance_action: str = "count-objects",
    force: bool = False,
) -> ForgeResult:
    with Timer() as t:
        if action not in ACTIONS:
            return ForgeResult.failure(
                TOOL,
                [f"Unknown action: {action}"],
                t.elapsed_ms,
                suggestion=f"Use one of: {', '.join(ACTIONS)}",
            )
        try:
            cmd = _build_command(
                action=action,
                execute=execute,
                remote=remote,
                remote_url=remote_url,
                branch=branch,
                ref=ref,
                path=path,
                paths=paths,
                staged=staged,
                create=create,
                rebase=rebase,
                ff_only=ff_only,
                source=source,
                reset_mode=reset_mode,
                prune=prune,
                include_dirs=include_dirs,
                force_with_lease=force_with_lease,
                patch=patch,
                count=count,
                rebase_action=rebase_action,
                bisect_action=bisect_action,
                maintenance_action=maintenance_action,
                force=force,
            )
        except ValueError as exc:
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)

        command = shlex.join(cmd)
        if action in MUTATING_ACTIONS and not execute:
            return ForgeResult.success(
                TOOL,
                {
                    "action": action,
                    "executed": False,
                    "preview": True,
                    "command": command,
                    "requires_confirmation": True,
                },
                t.elapsed_ms,
            )
        if action in MUTATING_ACTIONS and not confirm:
            return ForgeResult.failure(
                TOOL,
                ["Explicit confirmation is required for this git mutation"],
                t.elapsed_ms,
                suggestion="Call again with execute=true and confirm=true after reviewing the preview",
            )

        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=120)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["git not found"], t.elapsed_ms, "Install git")
        except Exception as exc:
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"git exited with code {rc}"],
                t.elapsed_ms,
                suggestion="Inspect the repository state and review the command before retrying",
            )

        output = stdout.strip()
        if action == "remote":
            data = {"action": action, "remotes": _parse_remotes(output)}
        else:
            if max_lines > 0:
                output_lines = output.splitlines()
                truncated = len(output_lines) > max_lines
                output = "\n".join(output_lines[:max_lines])
            else:
                truncated = False
            data = {
                "action": action,
                "executed": True,
                "preview": False,
                "command": command,
                "output": output,
                "truncated": truncated,
            }
        return ForgeResult.success(TOOL, data, t.elapsed_ms)


def _build_command(
    *,
    action: str,
    execute: bool,
    remote: str,
    remote_url: str,
    branch: str,
    ref: str,
    path: str,
    paths: str,
    staged: bool,
    create: bool,
    rebase: bool,
    ff_only: bool,
    source: str,
    reset_mode: str,
    prune: bool,
    include_dirs: bool,
    force_with_lease: bool,
    patch: bool,
    count: int,
    rebase_action: str,
    bisect_action: str,
    maintenance_action: str,
    force: bool,
) -> list[str]:
    _validate_tokens(remote, remote_url, branch, ref, path, source)
    if action == "remote":
        return ["git", "remote", "-v"]
    if action == "show":
        cmd = ["git", "show", "--format=fuller", "--stat", "--decorate"]
        if patch:
            cmd.append("--patch")
        cmd.append(ref or "HEAD")
        if path:
            cmd += ["--", path]
        return cmd
    if action == "reflog":
        return ["git", "reflog", "--date=iso", f"-n{max(count, 1)}", ref or "HEAD"]
    if action == "fetch":
        cmd = ["git", "fetch"]
        if prune:
            cmd.append("--prune")
        cmd.append(remote)
        if branch:
            cmd.append(branch)
        return cmd
    if action == "pull":
        cmd = ["git", "pull", "--rebase" if rebase else "--ff-only"]
        if remote:
            cmd.append(remote)
        if branch:
            cmd.append(branch)
        return cmd
    if action == "push":
        cmd = ["git", "push"]
        if force_with_lease:
            cmd.append("--force-with-lease")
        if create:
            cmd.append("--set-upstream")
        cmd.append(remote)
        if branch:
            cmd.append(branch)
        return cmd
    if action == "branch-create":
        if not branch:
            raise ValueError("branch is required for action=branch-create")
        return ["git", "branch", branch, ref or "HEAD"]
    if action == "branch-delete":
        if not branch:
            raise ValueError("branch is required for action=branch-delete")
        return ["git", "branch", "-D" if force else "-d", branch]
    if action == "remote-add":
        if not remote or not remote_url:
            raise ValueError("remote and remote_url are required for action=remote-add")
        return ["git", "remote", "add", remote, remote_url]
    if action == "remote-remove":
        return ["git", "remote", "remove", remote]
    if action == "remote-set-url":
        if not remote_url:
            raise ValueError("remote_url is required for action=remote-set-url")
        return ["git", "remote", "set-url", remote, remote_url]
    if action == "remote-prune":
        return ["git", "remote", "prune", remote]
    if action == "switch":
        if not branch:
            raise ValueError("branch is required for action=switch")
        return ["git", "switch", "--create" if create else "--", branch]
    if action == "restore":
        selected = [item.strip() for item in (paths or path).split(",") if item.strip()]
        if not selected:
            raise ValueError("path or paths is required for action=restore")
        _validate_tokens(*selected)
        cmd = ["git", "restore"]
        if source:
            cmd += ["--source", source]
        if staged:
            cmd.append("--staged")
        return [*cmd, "--", *selected]
    if action == "merge":
        if not branch:
            raise ValueError("branch is required for action=merge")
        cmd = ["git", "merge"]
        if ff_only:
            cmd.append("--ff-only")
        else:
            cmd.append("--no-edit")
        return [*cmd, branch]
    if action == "rebase":
        if rebase_action not in {"", "abort", "continue", "skip"}:
            raise ValueError("rebase_action must be abort, continue, or skip")
        if rebase_action:
            return ["git", "rebase", f"--{rebase_action}"]
        if not branch:
            raise ValueError("branch is required for action=rebase")
        return ["git", "rebase", branch]
    if action == "reset":
        if reset_mode not in {"soft", "mixed", "hard", "keep", "merge"}:
            raise ValueError("reset_mode must be soft, mixed, hard, keep, or merge")
        if not ref:
            raise ValueError("ref is required for action=reset")
        return ["git", "reset", f"--{reset_mode}", ref]
    if action == "revert":
        if not ref:
            raise ValueError("ref is required for action=revert")
        return ["git", "revert", "--no-edit", ref]
    if action == "bisect":
        if bisect_action not in {"start", "bad", "good", "skip", "reset"}:
            raise ValueError("bisect_action must be start, bad, good, skip, or reset")
        cmd = ["git", "bisect", bisect_action]
        if ref:
            cmd.append(ref)
        return cmd
    if action == "clean":
        cmd = ["git", "clean", "-n" if not execute else "-f"]
        if include_dirs:
            cmd.append("-d")
        return cmd
    if action == "maintenance":
        if maintenance_action == "count-objects":
            return ["git", "count-objects", "-vH"]
        if maintenance_action == "gc":
            return ["git", "gc"]
        if maintenance_action == "fsck":
            return ["git", "fsck", "--no-progress"]
        raise ValueError("maintenance_action must be count-objects, gc, or fsck")
    raise ValueError(f"Unsupported action: {action}")


def _validate_tokens(*values: str) -> None:
    for value in values:
        if value and value.startswith("-"):
            raise ValueError(f"Git ref/path cannot start with '-': {value}")


def _parse_remotes(output: str) -> list[dict[str, str]]:
    remotes = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            remotes.append({"name": parts[0], "url": parts[1], "kind": parts[2].strip("()")})
    return remotes


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=ACTIONS)
    p.add_argument("--execute", action="store_true", help="Execute a mutating action; preview is the default")
    p.add_argument("--confirm", action="store_true", help="Confirm the reviewed mutating command")
    p.add_argument("--remote", default="origin")
    p.add_argument("--remote-url", default="")
    p.add_argument("--branch", default="")
    p.add_argument("--ref", default="")
    p.add_argument("--path", default="")
    p.add_argument("--paths", default="", help="Comma-separated paths for restore")
    p.add_argument("--staged", action="store_true", help="Restore the index as well as the worktree")
    p.add_argument("--create", action="store_true", help="Create branch or set upstream, depending on action")
    p.add_argument("--rebase", action="store_true")
    p.add_argument("--no-ff-only", dest="ff_only", action="store_false", default=True)
    p.add_argument("--source", default="")
    p.add_argument("--reset-mode", default="mixed")
    p.add_argument("--prune", action="store_true")
    p.add_argument("--include-dirs", action="store_true")
    p.add_argument("--force-with-lease", action="store_true")
    p.add_argument("--patch", action="store_true")
    p.add_argument("--max-lines", type=int, default=200)
    p.add_argument("--count", type=int, default=20)
    p.add_argument("--rebase-action", default="")
    p.add_argument("--bisect-action", default="")
    p.add_argument("--maintenance-action", default="count-objects", choices=["count-objects", "gc", "fsck"])
    p.add_argument("--force", action="store_true", help="Force branch deletion with -D")


if __name__ == "__main__":
    make_cli(TOOL, "Preview or execute operational git actions with explicit confirmation", run, _add_args)
