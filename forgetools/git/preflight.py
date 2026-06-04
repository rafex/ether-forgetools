"""forgetools.git.preflight - Validate branch, remote, and protection status before push or merge."""
from __future__ import annotations

import argparse
import json
from urllib.parse import quote

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command


def _git(args: list[str], cwd: str | None) -> tuple[bool, str]:
    rc, out, err = run_command(["git", *args], cwd=cwd)
    return rc == 0, (out or err).strip()


def _gh_json(args: list[str], cwd: str | None) -> tuple[bool, object | str]:
    rc, out, err = run_command(["gh", *args], cwd=cwd)
    if rc != 0:
        return False, err.strip() or out.strip()
    try:
        return True, json.loads(out) if out.strip() else None
    except json.JSONDecodeError:
        return False, out.strip()


def run(*, action: str = "push", branch: str = "", remote: str = "origin", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        ok_branch, current = _git(["branch", "--show-current"], cwd)
        target_branch = branch or current
        checks = []
        errors = []

        checks.append({"name": "inside_git_repo", "ok": ok_branch, "detail": current})
        if not ok_branch:
            return ForgeResult.failure("git.preflight", ["Not inside a git repository"], t.elapsed_ms)

        ok_remote, remote_url = _git(["remote", "get-url", remote], cwd)
        checks.append({"name": "remote_exists", "ok": ok_remote, "detail": remote_url})
        if not ok_remote:
            errors.append(f"Remote '{remote}' does not exist")

        ok_upstream, upstream = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd)
        checks.append({"name": "upstream_configured", "ok": ok_upstream, "detail": upstream})

        ok_dirty, dirty = _git(["status", "--porcelain"], cwd)
        clean = ok_dirty and not dirty
        checks.append({"name": "working_tree_clean", "ok": clean, "detail": dirty})
        if action in {"push", "merge"} and not clean:
            errors.append("Working tree is not clean")

        protected = None
        encoded_branch = quote(target_branch, safe="")
        ok_protect, protection = _gh_json(["api", f"repos/{{owner}}/{{repo}}/branches/{encoded_branch}/protection"], cwd)
        if ok_protect:
            protected = True
        else:
            protected = False if "404" in str(protection) or "Not Found" in str(protection) else None
        checks.append({"name": "branch_protection_checked", "ok": ok_protect or protected is False, "detail": protection if not ok_protect else "protected"})

        if action == "merge" and protected is False:
            errors.append(f"Branch '{target_branch}' does not appear protected")

        allowed = not errors
        return ForgeResult.success(
            "git.preflight",
            {
                "action": action,
                "branch": target_branch,
                "remote": remote,
                "remote_url": remote_url if ok_remote else None,
                "upstream": upstream if ok_upstream else None,
                "protected": protected,
                "allowed": allowed,
                "checks": checks,
                "errors": errors,
            },
            t.elapsed_ms,
        )


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="push", choices=["push", "merge", "release"], help="Operation to validate")
    p.add_argument("--branch", default="", help="Target branch, default current branch")
    p.add_argument("--remote", default="origin", help="Remote name")


if __name__ == "__main__":
    make_cli("git.preflight", "Validate branch, remote, and protection status before push or merge", run, _args)
