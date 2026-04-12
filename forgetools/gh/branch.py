from __future__ import annotations

"""
gh/branch.py — Manage GitHub repository branches (requires gh CLI + auth).

Actions:
    list        — list branches (local or remote)
    create      — create a new branch from a base ref
    delete      — delete a branch (local and/or remote)
    rename      — rename a branch (local + remote push)
    default     — get or set the default branch of the repo
    protect     — show branch protection rules for a branch
    sync        — sync a fork branch with upstream (gh CLI sync)
    stale       — find branches that haven't been updated in N days
"""

import argparse
import json
from datetime import datetime, timezone

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "gh.branch"


def _gh(*args: str, cwd: str | None = None, timeout: int = 30) -> tuple[int, str, str]:
    return run_command(["gh", *args], cwd=cwd, timeout=timeout)


def _git(*args: str, cwd: str | None = None, timeout: int = 15) -> tuple[int, str, str]:
    return run_command(["git", *args], cwd=cwd, timeout=timeout)


def run(
    *,
    action:     str = "list",
    branch:     str | None = None,
    base:       str = "main",
    new_name:   str | None = None,
    remote:     bool = True,
    local:      bool = True,
    force:      bool = False,
    days_stale: int = 90,
    set_default: str | None = None,   # branch name to set as default
    cwd:        str | None = None,
) -> ForgeResult:
    with Timer() as t:

        if action == "list":
            # List remote branches via gh api
            rc, stdout, stderr = _gh(
                "api", "repos/{owner}/{repo}/branches", "--paginate",
                "--jq", "[.[] | {name: .name, protected: .protected, sha: .commit.sha[0:10]}]",
                cwd=cwd,
            )
            if rc != 0:
                # fallback to git branch
                rc2, out2, _ = _git("branch", "-a", "--format=%(refname:short)", cwd=cwd)
                branches = [b.strip() for b in out2.splitlines() if b.strip()]
                return ForgeResult.success(TOOL, {"count": len(branches), "branches": branches, "source": "git"}, t.elapsed_ms)

            # gh api --paginate returns multiple JSON arrays, merge them
            import re
            arrays = re.findall(r'\[.*?\]', stdout, re.DOTALL)
            branches: list[dict] = []
            for a in arrays:
                try:
                    branches.extend(json.loads(a))
                except json.JSONDecodeError:
                    pass
            return ForgeResult.success(TOOL, {
                "count":    len(branches),
                "source":   "github_api",
                "branches": branches,
            }, t.elapsed_ms)

        if action == "create":
            if not branch:
                return ForgeResult.failure(TOOL, ["--branch is required for action=create"], t.elapsed_ms)
            # Create locally and push
            rc, stdout, stderr = _git("checkout", "-b", branch, base, cwd=cwd)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            rc2, out2, err2 = _git("push", "-u", "origin", branch, cwd=cwd)
            if rc2 != 0:
                return ForgeResult.failure(TOOL, [err2.strip()], t.elapsed_ms,
                                           suggestion="Branch created locally but push failed")
            return ForgeResult.success(TOOL, {
                "created": True,
                "branch":  branch,
                "base":    base,
                "pushed":  True,
            }, t.elapsed_ms)

        if action == "delete":
            if not branch:
                return ForgeResult.failure(TOOL, ["--branch is required for action=delete"], t.elapsed_ms)
            errors = []
            deleted_local = deleted_remote = False

            if local:
                flag = "-D" if force else "-d"
                rc, _, err = _git("branch", flag, branch, cwd=cwd)
                if rc == 0:
                    deleted_local = True
                else:
                    errors.append(f"local: {err.strip()}")

            if remote:
                rc2, _, err2 = _git("push", "origin", "--delete", branch, cwd=cwd)
                if rc2 == 0:
                    deleted_remote = True
                else:
                    errors.append(f"remote: {err2.strip()}")

            if not deleted_local and not deleted_remote:
                return ForgeResult.failure(TOOL, errors, t.elapsed_ms)
            return ForgeResult.success(TOOL, {
                "branch":         branch,
                "deleted_local":  deleted_local,
                "deleted_remote": deleted_remote,
                "errors":         errors,
            }, t.elapsed_ms)

        if action == "rename":
            if not branch or not new_name:
                return ForgeResult.failure(TOOL, ["--branch and --new-name are required for action=rename"], t.elapsed_ms)
            rc, _, err = _git("branch", "-m", branch, new_name, cwd=cwd)
            if rc != 0:
                return ForgeResult.failure(TOOL, [err.strip()], t.elapsed_ms)
            rc2, _, err2 = _git("push", "origin", "--delete", branch, cwd=cwd)
            rc3, _, err3 = _git("push", "-u", "origin", new_name, cwd=cwd)
            return ForgeResult.success(TOOL, {
                "renamed":    True,
                "old_name":   branch,
                "new_name":   new_name,
                "remote_old_deleted": rc2 == 0,
                "remote_new_pushed":  rc3 == 0,
            }, t.elapsed_ms)

        if action == "default":
            if set_default:
                rc, stdout, stderr = _gh(
                    "api", "--method", "PATCH", "repos/{owner}/{repo}",
                    "-f", f"default_branch={set_default}",
                    "--jq", ".default_branch",
                    cwd=cwd,
                )
                if rc != 0:
                    return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
                return ForgeResult.success(TOOL, {"default_branch": stdout.strip().strip('"')}, t.elapsed_ms)
            else:
                rc, stdout, stderr = _gh(
                    "api", "repos/{owner}/{repo}", "--jq", ".default_branch", cwd=cwd
                )
                if rc != 0:
                    return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
                return ForgeResult.success(TOOL, {"default_branch": stdout.strip().strip('"')}, t.elapsed_ms)

        if action == "protect":
            if not branch:
                return ForgeResult.failure(TOOL, ["--branch is required for action=protect"], t.elapsed_ms)
            rc, stdout, stderr = _gh(
                "api", f"repos/{{owner}}/{{repo}}/branches/{branch}/protection",
                cwd=cwd,
            )
            if rc != 0:
                if "404" in stderr or "Branch not protected" in stderr:
                    return ForgeResult.success(TOOL, {"branch": branch, "protected": False}, t.elapsed_ms)
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            try:
                rules = json.loads(stdout)
                return ForgeResult.success(TOOL, {
                    "branch":    branch,
                    "protected": True,
                    "rules":     {
                        "required_status_checks":    rules.get("required_status_checks"),
                        "enforce_admins":             (rules.get("enforce_admins") or {}).get("enabled"),
                        "required_pull_request_reviews": bool(rules.get("required_pull_request_reviews")),
                        "restrictions":              bool(rules.get("restrictions")),
                        "allow_force_pushes":        (rules.get("allow_force_pushes") or {}).get("enabled"),
                        "allow_deletions":           (rules.get("allow_deletions") or {}).get("enabled"),
                    },
                }, t.elapsed_ms)
            except json.JSONDecodeError:
                return ForgeResult.success(TOOL, {"branch": branch, "protected": True, "raw": stdout}, t.elapsed_ms)

        if action == "sync":
            if not branch:
                return ForgeResult.failure(TOOL, ["--branch is required for action=sync"], t.elapsed_ms)
            rc, stdout, stderr = _gh("repo", "sync", "--branch", branch, cwd=cwd)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"synced": True, "branch": branch, "output": stdout.strip()}, t.elapsed_ms)

        if action == "stale":
            rc, stdout, stderr = _gh(
                "api", "repos/{owner}/{repo}/branches", "--paginate",
                "--jq", "[.[] | {name: .name, sha: .commit.sha}]",
                cwd=cwd,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)

            import re as _re
            arrays = _re.findall(r'\[.*?\]', stdout, _re.DOTALL)
            branches_raw: list[dict] = []
            for a in arrays:
                try:
                    branches_raw.extend(json.loads(a))
                except Exception:
                    pass

            stale = []
            now = datetime.now(tz=timezone.utc)
            for b in branches_raw:
                name = b["name"]
                sha  = b["sha"]
                rc2, out2, _ = _gh(
                    "api", f"repos/{{owner}}/{{repo}}/commits/{sha}",
                    "--jq", ".commit.committer.date",
                    cwd=cwd,
                )
                if rc2 != 0:
                    continue
                try:
                    date_str = out2.strip().strip('"')
                    commit_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    age_days = (now - commit_date).days
                    if age_days >= days_stale:
                        stale.append({"name": name, "age_days": age_days, "last_commit": date_str})
                except Exception:
                    pass

            stale.sort(key=lambda x: -x["age_days"])
            return ForgeResult.success(TOOL, {
                "total_branches": len(branches_raw),
                "stale_count":    len(stale),
                "stale_after_days": days_stale,
                "stale_branches": stale,
            }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: list | create | delete | rename | default | protect | sync | stale"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action",  default="list",
                   choices=["list", "create", "delete", "rename", "default", "protect", "sync", "stale"])
    p.add_argument("--branch",       default=None)
    p.add_argument("--base",         default="main", help="Base branch/ref for create (default: main)")
    p.add_argument("--new-name",     default=None, dest="new_name", help="New branch name for rename")
    p.add_argument("--no-remote",    action="store_false", dest="remote", help="Skip remote operations")
    p.add_argument("--no-local",     action="store_false", dest="local",  help="Skip local operations")
    p.add_argument("--force",        action="store_true",  help="Force delete even if unmerged")
    p.add_argument("--days-stale",   type=int, default=90, dest="days_stale")
    p.add_argument("--set-default",  default=None, dest="set_default", help="Set as default branch")
    p.add_argument("--cwd",          default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Manage GitHub repository branches (requires gh auth)", run, _add_args)
