from __future__ import annotations

"""
git/multi_repo.py — Health check for multiple independent git repos under a base dir.

Designed for "side-by-side" repo layouts where each subdirectory is its own
git repository (not git submodules).  For each repo it checks:

    1. Working directory changes  (git status --porcelain)
    2. Sync with remote branch    (git fetch + SHA comparison)
    3. Ahead / behind counts      (git rev-list --count)
    4. Source-file license header (grep for a copyright string)

Actions:
    check   — full health check on every discovered repo (default)
    status  — working-directory status only (fast, no fetch)
    summary — aggregate: totals, dirty count, out-of-sync count, missing-license count

Discovery:
    1. If --modules is given, use exactly those subdirectory names.
    2. Otherwise scan --dir for subdirs matching --pattern that contain a .git entry.

Generic flags:
    --dir DIR              Base directory (default: cwd)
    --pattern GLOB         Glob filter for subdirectory names (default: *)
    --modules a,b,c        Comma-separated explicit module list (overrides --pattern)
    --branch BRANCH        Remote branch to compare (default: main)
    --remote REMOTE        Remote name (default: origin)
    --license-header STR   String to search in source files (default: "Copyright (C)")
    --source-ext EXT       Comma-separated file extensions to scan (default: .java)
    --no-fetch             Skip `git fetch` (faster, but sync info may be stale)
    --no-license           Skip license header check
"""

import argparse
import fnmatch
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.multi_repo"

_DEFAULT_LICENSE = "Copyright (C)"
_DEFAULT_EXTS    = ".java"
_DEFAULT_BRANCH  = "main"
_DEFAULT_REMOTE  = "origin"


# ── per-repo checks ───────────────────────────────────────────────────────────

def _working_dir_status(repo: Path) -> dict:
    rc, out, _ = run_command(["git", "status", "--porcelain"], cwd=str(repo), timeout=10)
    if rc != 0:
        return {"ok": False, "error": "git status failed", "changes": []}
    lines = [l for l in out.splitlines() if l.strip()]
    return {"ok": True, "clean": not lines, "changes": lines}


def _fetch(repo: Path, remote: str, branch: str) -> bool:
    rc, _, _ = run_command(
        ["git", "fetch", remote, branch],
        cwd=str(repo), timeout=30,
    )
    return rc == 0


def _sync_info(repo: Path, remote: str, branch: str) -> dict:
    """Returns local SHA, remote SHA, ahead, behind counts."""
    local_rc,  local_sha,  _ = run_command(
        ["git", "rev-parse", branch], cwd=str(repo), timeout=5
    )
    remote_rc, remote_sha, _ = run_command(
        ["git", "rev-parse", f"{remote}/{branch}"], cwd=str(repo), timeout=5
    )

    local_sha  = local_sha.strip()  if local_rc  == 0 else "N/A"
    remote_sha = remote_sha.strip() if remote_rc == 0 else "N/A"
    in_sync    = (local_rc == 0 and remote_rc == 0 and local_sha == remote_sha)

    ahead = behind = 0
    if local_rc == 0 and remote_rc == 0:
        rc_a, out_a, _ = run_command(
            ["git", "rev-list", "--count", f"{remote}/{branch}..{branch}"],
            cwd=str(repo), timeout=5,
        )
        rc_b, out_b, _ = run_command(
            ["git", "rev-list", "--count", f"{branch}..{remote}/{branch}"],
            cwd=str(repo), timeout=5,
        )
        if rc_a == 0:
            ahead  = int(out_a.strip() or 0)
        if rc_b == 0:
            behind = int(out_b.strip() or 0)

    return {
        "in_sync":    in_sync,
        "local_sha":  local_sha[:10] if local_sha  != "N/A" else "N/A",
        "remote_sha": remote_sha[:10] if remote_sha != "N/A" else "N/A",
        "ahead":      ahead,   # commits to push
        "behind":     behind,  # commits to pull
    }


def _license_check(repo: Path, header: str, extensions: list[str]) -> dict:
    """Search source files for a license header string."""
    import subprocess

    # Build find command: find . -name "*.java" -o -name "*.py" ...
    # Then grep for the header string in those files.
    for ext in extensions:
        ext = ext.lstrip(".")
        rc, out, _ = run_command(
            ["grep", "-rl", header, "--include", f"*.{ext}", "."],
            cwd=str(repo), timeout=15,
        )
        if rc == 0 and out.strip():
            return {"found": True, "sample": out.splitlines()[0].strip()}

    return {"found": False, "sample": None}


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


# ── discovery ─────────────────────────────────────────────────────────────────

def _discover_repos(base: Path, pattern: str, modules: list[str] | None) -> list[Path]:
    """Return sorted list of repo Paths to check."""
    if modules:
        paths = []
        for m in modules:
            p = base / m
            if p.is_dir():
                paths.append(p)
        return paths

    candidates = sorted(d for d in base.iterdir() if d.is_dir() and not d.name.startswith("."))
    if pattern and pattern != "*":
        candidates = [d for d in candidates if fnmatch.fnmatch(d.name, pattern)]

    return [d for d in candidates if _is_git_repo(d)]


# ── single repo check ─────────────────────────────────────────────────────────

def _check_repo(
    repo: Path,
    *,
    remote: str,
    branch: str,
    do_fetch: bool,
    do_license: bool,
    license_header: str,
    source_extensions: list[str],
) -> dict:
    entry: dict = {"name": repo.name, "path": str(repo)}

    if not _is_git_repo(repo):
        entry["error"] = "not a git repository"
        entry["healthy"] = False
        return entry

    # 1. Working directory
    wd = _working_dir_status(repo)
    entry["working_dir"] = wd

    # 2. Fetch + sync
    fetch_ok = True
    if do_fetch:
        fetch_ok = _fetch(repo, remote, branch)
        entry["fetch_ok"] = fetch_ok

    sync = _sync_info(repo, remote, branch)
    entry["sync"] = sync

    # 3. License
    if do_license:
        lic = _license_check(repo, license_header, source_extensions)
        entry["license"] = lic

    # 4. Healthy flag
    healthy = (
        wd.get("clean", True)
        and sync.get("in_sync", True)
        and sync.get("ahead", 0) == 0
        and sync.get("behind", 0) == 0
        and (not do_license or entry.get("license", {}).get("found", True))
    )
    entry["healthy"] = healthy
    return entry


# ── actions ───────────────────────────────────────────────────────────────────

def _action_check(
    repos: list[Path], *, remote, branch, do_fetch, do_license, license_header, source_exts
) -> dict:
    results = []
    for repo in repos:
        results.append(_check_repo(
            repo, remote=remote, branch=branch,
            do_fetch=do_fetch, do_license=do_license,
            license_header=license_header, source_extensions=source_exts,
        ))
    healthy_count = sum(1 for r in results if r.get("healthy"))
    return {
        "total":   len(results),
        "healthy": healthy_count,
        "issues":  len(results) - healthy_count,
        "repos":   results,
    }


def _action_status(repos: list[Path]) -> dict:
    results = []
    for repo in repos:
        if not _is_git_repo(repo):
            results.append({"name": repo.name, "error": "not a git repository"})
            continue
        wd = _working_dir_status(repo)
        results.append({"name": repo.name, "path": str(repo), **wd})
    dirty = sum(1 for r in results if not r.get("clean", True))
    return {"total": len(results), "dirty": dirty, "repos": results}


def _action_summary(
    repos: list[Path], *, remote, branch, do_fetch, do_license, license_header, source_exts
) -> dict:
    data = _action_check(
        repos, remote=remote, branch=branch,
        do_fetch=do_fetch, do_license=do_license,
        license_header=license_header, source_exts=source_exts,
    )
    dirty             = [r["name"] for r in data["repos"] if not r.get("working_dir", {}).get("clean", True)]
    out_of_sync       = [r["name"] for r in data["repos"] if not r.get("sync", {}).get("in_sync", True)]
    need_push         = [r["name"] for r in data["repos"] if r.get("sync", {}).get("ahead", 0) > 0]
    need_pull         = [r["name"] for r in data["repos"] if r.get("sync", {}).get("behind", 0) > 0]
    missing_license   = [r["name"] for r in data["repos"] if do_license and not r.get("license", {}).get("found", True)]
    not_git           = [r["name"] for r in data["repos"] if "error" in r]

    return {
        "total":           data["total"],
        "healthy":         data["healthy"],
        "dirty_count":     len(dirty),
        "out_of_sync_count": len(out_of_sync),
        "need_push_count": len(need_push),
        "need_pull_count": len(need_pull),
        "missing_license_count": len(missing_license),
        "dirty":           dirty,
        "out_of_sync":     out_of_sync,
        "need_push":       need_push,
        "need_pull":       need_pull,
        "missing_license": missing_license,
        "not_git_repos":   not_git,
    }


# ── public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action:          str         = "check",
    dir:             str | None  = None,
    pattern:         str         = "*",
    modules:         str | None  = None,   # comma-separated module names
    branch:          str         = _DEFAULT_BRANCH,
    remote:          str         = _DEFAULT_REMOTE,
    license_header:  str         = _DEFAULT_LICENSE,
    source_ext:      str         = _DEFAULT_EXTS,
    no_fetch:        bool        = False,
    no_license:      bool        = False,
    cwd:             str | None  = None,
) -> ForgeResult:
    with Timer() as t:
        base = Path(dir or cwd or ".").resolve()
        if not base.is_dir():
            return ForgeResult.failure(TOOL, [f"Directory not found: {base}"], t.elapsed_ms)

        module_list = [m.strip() for m in modules.split(",")] if modules else None
        repos = _discover_repos(base, pattern, module_list)

        if not repos:
            return ForgeResult.failure(
                TOOL,
                [f"No git repositories found under {base} matching pattern='{pattern}'"],
                t.elapsed_ms,
                suggestion="Use --pattern 'ether-*' or --modules to specify targets",
            )

        exts = [e.strip() for e in source_ext.split(",")]

        kw = dict(
            remote=remote, branch=branch,
            do_fetch=not no_fetch, do_license=not no_license,
            license_header=license_header, source_exts=exts,
        )

        if action == "check":
            data = _action_check(repos, **kw)
        elif action == "status":
            data = _action_status(repos)
        elif action == "summary":
            data = _action_summary(repos, **kw)
        else:
            return ForgeResult.failure(
                TOOL,
                [f"Unknown action '{action}'. Use: check | status | summary"],
                t.elapsed_ms,
            )

        ok = data.get("issues", 0) == 0 or action == "status"
        suggestion = None
        if not ok:
            parts = []
            if data.get("dirty_count", 0):
                parts.append(f"{data['dirty_count']} repo(s) with uncommitted changes")
            if data.get("out_of_sync_count", 0):
                parts.append(f"{data.get('out_of_sync_count',0)} repo(s) out of sync with {remote}/{branch}")
            if data.get("missing_license_count", 0):
                parts.append(f"{data['missing_license_count']} repo(s) missing license header")
            suggestion = "; ".join(parts) if parts else None

        return ForgeResult(
            ok=ok,
            tool=TOOL,
            data=data,
            errors=[] if ok else ["One or more repositories have health issues"],
            suggestion=suggestion,
            duration_ms=t.elapsed_ms,
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--action", default="check",
        choices=["check", "status", "summary"],
        help=(
            "check: full health check on all repos (default) | "
            "status: working-dir status only, no fetch | "
            "summary: aggregate counts and lists of problem repos"
        ),
    )
    p.add_argument("--dir", default=None,
                   help="Base directory containing the repos (default: cwd)")
    p.add_argument("--pattern", default="*",
                   help="Glob filter for subdirectory names, e.g. 'ether-*' (default: *)")
    p.add_argument("--modules", default=None,
                   help="Comma-separated explicit module names (overrides --pattern)")
    p.add_argument("--branch", default=_DEFAULT_BRANCH,
                   help=f"Remote branch to compare against (default: {_DEFAULT_BRANCH})")
    p.add_argument("--remote", default=_DEFAULT_REMOTE,
                   help=f"Git remote name (default: {_DEFAULT_REMOTE})")
    p.add_argument("--license-header", default=_DEFAULT_LICENSE, dest="license_header",
                   help=f"String to search for in source files (default: '{_DEFAULT_LICENSE}')")
    p.add_argument("--source-ext", default=_DEFAULT_EXTS, dest="source_ext",
                   help=f"Comma-separated file extensions to check for license (default: {_DEFAULT_EXTS})")
    p.add_argument("--no-fetch", action="store_true", dest="no_fetch",
                   help="Skip git fetch (faster, sync info may be stale)")
    p.add_argument("--no-license", action="store_true", dest="no_license",
                   help="Skip license header check")
    p.add_argument("--cwd", default=None)


if __name__ == "__main__":
    make_cli(
        TOOL,
        "Health check for multiple independent git repos under a base directory",
        run,
        _add_args,
    )
