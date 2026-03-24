from __future__ import annotations

"""
gh/actions_validate.py — Semantic validator for GitHub Actions workflow YAML files.

Goes beyond "is this valid YAML?" — checks the workflow structure, field types,
action pinning, job dependency cycles, deprecated commands, and more.

Actions:
    validate   (default) — validate a single file or all workflows in a directory
    lint                 — alias for validate, stricter output grouping

Checks performed:
    Structure   — required fields (on/jobs), job fields (runs-on, steps),
                  step fields (uses OR run, not both)
    References  — needs: jobs must exist; no circular dependencies
    Pinning     — warns on @main/@master/@HEAD action refs (prefer @vN or SHA)
    Deprecations — set-output, save-state, ::set-output:: commands
    Permissions — valid permission values (read/write/none)
    Timeouts    — must be numeric; warn if > 360 min
    Matrix      — strategy.matrix must have at least one dimension
    Types       — env values must be strings/numbers; bool fields must be bool
    Secrets     — secrets.GITHUB_TOKEN used without permissions block (warn)
"""

import argparse
import re
from pathlib import Path
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "gh.actions_validate"

# ── Constants ─────────────────────────────────────────────────────────────────

VALID_TRIGGERS = {
    "branch_protection_rule", "check_run", "check_suite", "create", "delete",
    "deployment", "deployment_status", "discussion", "discussion_comment",
    "fork", "gollum", "issue_comment", "issues", "label", "merge_group",
    "milestone", "page_build", "project", "project_card", "project_column",
    "public", "pull_request", "pull_request_review", "pull_request_review_comment",
    "pull_request_target", "push", "registry_package", "release", "repository_dispatch",
    "schedule", "status", "watch", "workflow_call", "workflow_dispatch",
    "workflow_run",
}

VALID_PERMISSIONS = {"read", "write", "none"}

VALID_PERMISSION_SCOPES = {
    "actions", "attestations", "checks", "contents", "deployments", "discussions",
    "id-token", "issues", "packages", "pages", "pull-requests", "repository-projects",
    "security-events", "statuses",
}

KNOWN_RUNNERS = {
    "ubuntu-latest", "ubuntu-22.04", "ubuntu-20.04", "ubuntu-24.04",
    "windows-latest", "windows-2022", "windows-2019",
    "macos-latest", "macos-14", "macos-13", "macos-12",
}

DEPRECATED_COMMANDS = [
    ("::set-output",  "set-output is deprecated — use $GITHUB_OUTPUT"),
    ("::save-state",  "save-state is deprecated — use $GITHUB_STATE"),
    ("::set-env",     "set-env is deprecated — use $GITHUB_ENV"),
    ("::add-path",    "add-path is deprecated — use $GITHUB_PATH"),
]

_UNPIN_RE = re.compile(r"@(main|master|HEAD|latest)\s*$")
_SHA_RE   = re.compile(r"@[0-9a-f]{40}\b")

# ── Finding model ─────────────────────────────────────────────────────────────

def _finding(level: str, path: str, message: str, hint: str | None = None) -> dict:
    f: dict = {"level": level, "path": path, "message": message}
    if hint:
        f["hint"] = hint
    return f


def _err(path: str, msg: str, hint: str | None = None) -> dict:
    return _finding("error", path, msg, hint)


def _warn(path: str, msg: str, hint: str | None = None) -> dict:
    return _finding("warning", path, msg, hint)


def _info(path: str, msg: str, hint: str | None = None) -> dict:
    return _finding("info", path, msg, hint)


# ── Validators ────────────────────────────────────────────────────────────────

def _check_top_level(wf: dict) -> list[dict]:
    findings: list[dict] = []

    # `on` key — PyYAML parses bare `on` as Python True
    triggers = wf.get("on") or wf.get(True)
    if triggers is None:
        findings.append(_err("on", "Missing required field 'on' (trigger events)"))
    else:
        if isinstance(triggers, dict):
            unknown = set(triggers.keys()) - VALID_TRIGGERS
            for u in sorted(unknown):
                findings.append(_warn(f"on.{u}", f"Unknown trigger event '{u}'"))
        elif isinstance(triggers, list):
            unknown = set(triggers) - VALID_TRIGGERS
            for u in sorted(unknown):
                findings.append(_warn(f"on[{u}]", f"Unknown trigger event '{u}'"))

    if "jobs" not in wf:
        findings.append(_err("jobs", "Missing required field 'jobs'"))
    elif not isinstance(wf["jobs"], dict) or not wf["jobs"]:
        findings.append(_err("jobs", "'jobs' must be a non-empty mapping"))

    return findings


def _check_permissions(perms: Any, path: str) -> list[dict]:
    findings: list[dict] = []
    if isinstance(perms, str):
        if perms not in VALID_PERMISSIONS:
            findings.append(_err(path, f"Invalid permission value '{perms}' — use read/write/none"))
    elif isinstance(perms, dict):
        for scope, value in perms.items():
            if scope not in VALID_PERMISSION_SCOPES:
                findings.append(_warn(f"{path}.{scope}", f"Unknown permission scope '{scope}'"))
            elif value not in VALID_PERMISSIONS:
                findings.append(_err(f"{path}.{scope}", f"Invalid value '{value}' — use read/write/none"))
    return findings


def _check_step(step: Any, job_id: str, idx: int) -> list[dict]:
    findings: list[dict] = []
    base = f"jobs.{job_id}.steps[{idx}]"

    if not isinstance(step, dict):
        findings.append(_err(base, "Step must be a mapping"))
        return findings

    has_uses = "uses" in step
    has_run  = "run"  in step

    if not has_uses and not has_run:
        findings.append(_err(base, "Step must have either 'uses' or 'run'"))
    if has_uses and has_run:
        findings.append(_err(base, "Step cannot have both 'uses' and 'run'"))

    # Action pinning
    if has_uses:
        uses = str(step["uses"])
        if _UNPIN_RE.search(uses):
            findings.append(_warn(
                f"{base}.uses",
                f"Action '{uses}' is pinned to a mutable ref — use a version tag or SHA",
                hint="Example: actions/checkout@v4  or  actions/checkout@<sha>",
            ))
        elif not _SHA_RE.search(uses) and "@" in uses:
            # Has a ref but not a SHA — acceptable, just info if it's a tag
            pass

    # Deprecated run commands
    if has_run:
        run_text = str(step.get("run", ""))
        for cmd, msg in DEPRECATED_COMMANDS:
            if cmd in run_text:
                findings.append(_warn(f"{base}.run", msg))

    # timeout-minutes type
    if "timeout-minutes" in step:
        tm = step["timeout-minutes"]
        if not isinstance(tm, (int, float)):
            findings.append(_err(f"{base}.timeout-minutes", "timeout-minutes must be a number"))
        elif tm > 360:
            findings.append(_warn(f"{base}.timeout-minutes", f"timeout-minutes={tm} exceeds 360 — jobs are limited to 6 hours"))

    # continue-on-error type
    if "continue-on-error" in step:
        coe = step["continue-on-error"]
        if not isinstance(coe, bool) and not (isinstance(coe, str) and "${{" in coe):
            findings.append(_warn(f"{base}.continue-on-error", "continue-on-error should be a boolean"))

    # env values should be strings/numbers
    if "env" in step and isinstance(step["env"], dict):
        for k, v in step["env"].items():
            if isinstance(v, dict):
                findings.append(_warn(f"{base}.env.{k}", "env value is a nested mapping — expected string or number"))

    return findings


def _check_job(job_id: str, job: Any, all_job_ids: set[str]) -> list[dict]:
    findings: list[dict] = []
    base = f"jobs.{job_id}"

    if not isinstance(job, dict):
        findings.append(_err(base, "Job must be a mapping"))
        return findings

    # runs-on (not required for reusable workflow calls)
    is_reusable_call = isinstance(job.get("uses"), str)
    if not is_reusable_call:
        if "runs-on" not in job:
            findings.append(_err(f"{base}.runs-on", "Missing required field 'runs-on'"))
        else:
            runner = job["runs-on"]
            if isinstance(runner, str) and runner not in KNOWN_RUNNERS and "${{" not in runner:
                findings.append(_info(f"{base}.runs-on", f"Unknown runner '{runner}' — ok if it's a self-hosted label"))

    # needs references
    needs = job.get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    for dep in needs:
        if dep not in all_job_ids:
            findings.append(_err(f"{base}.needs", f"References unknown job '{dep}'"))

    # steps
    if not is_reusable_call:
        steps = job.get("steps")
        if steps is None:
            findings.append(_err(f"{base}.steps", "Missing required field 'steps'"))
        elif not isinstance(steps, list) or not steps:
            findings.append(_err(f"{base}.steps", "'steps' must be a non-empty list"))
        else:
            for i, step in enumerate(steps):
                findings.extend(_check_step(step, job_id, i))

    # permissions at job level
    if "permissions" in job:
        findings.extend(_check_permissions(job["permissions"], f"{base}.permissions"))

    # timeout-minutes
    if "timeout-minutes" in job:
        tm = job["timeout-minutes"]
        if not isinstance(tm, (int, float)):
            findings.append(_err(f"{base}.timeout-minutes", "timeout-minutes must be a number"))
        elif tm > 360:
            findings.append(_warn(f"{base}.timeout-minutes", f"timeout-minutes={tm} exceeds the 6-hour job limit"))

    # strategy.matrix
    if "strategy" in job:
        strategy = job["strategy"]
        if isinstance(strategy, dict) and "matrix" in strategy:
            matrix = strategy["matrix"]
            if isinstance(matrix, dict) and not any(
                k for k in matrix if k not in ("include", "exclude")
            ):
                findings.append(_warn(f"{base}.strategy.matrix", "Matrix has no dimensions (only include/exclude)"))

    # env values
    if "env" in job and isinstance(job["env"], dict):
        for k, v in job["env"].items():
            if isinstance(v, dict):
                findings.append(_warn(f"{base}.env.{k}", "env value is a nested mapping — expected string or number"))

    return findings


def _check_cycles(jobs: dict) -> list[dict]:
    """Detect circular job dependencies via DFS."""
    findings: list[dict] = []
    graph: dict[str, list[str]] = {}
    for jid, job in jobs.items():
        if not isinstance(job, dict):
            continue
        needs = job.get("needs", [])
        graph[jid] = [needs] if isinstance(needs, str) else list(needs)

    visited:    set[str] = set()
    in_stack:   set[str] = set()

    def dfs(node: str) -> bool:
        visited.add(node)
        in_stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in in_stack:
                return True
        in_stack.discard(node)
        return False

    for job_id in graph:
        if job_id not in visited:
            if dfs(job_id):
                findings.append(_err("jobs", f"Circular dependency detected involving job '{job_id}'"))
                break

    return findings


def _check_secrets_without_permissions(wf: dict) -> list[dict]:
    """Warn if GITHUB_TOKEN secrets are used but no top-level permissions block."""
    findings: list[dict] = []
    if "permissions" in wf:
        return findings
    # Scan for secrets.GITHUB_TOKEN usage
    text = str(wf)
    if "secrets.GITHUB_TOKEN" in text or "secrets.github_token" in text.lower():
        findings.append(_warn(
            "permissions",
            "Workflow uses secrets.GITHUB_TOKEN but has no 'permissions' block",
            hint="Add 'permissions: contents: read' (or narrower) to follow least-privilege",
        ))
    return findings


# ── Main validation entry point ───────────────────────────────────────────────

def _validate_workflow(content: str, filename: str) -> dict:
    """Validate a single workflow string. Returns validation result dict."""
    if not _HAS_YAML:
        return {
            "file":   filename,
            "valid":  False,
            "errors": 1, "warnings": 0,
            "findings": [_err("*", "pyyaml not installed — run: pip install pyyaml")],
        }

    # 1. Parse YAML
    try:
        wf = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        return {
            "file":   filename,
            "valid":  False,
            "errors": 1, "warnings": 0,
            "findings": [_err("yaml", f"YAML parse error: {exc}")],
        }

    if not isinstance(wf, dict):
        return {
            "file":   filename,
            "valid":  False,
            "errors": 1, "warnings": 0,
            "findings": [_err("*", "Workflow must be a YAML mapping at the top level")],
        }

    findings: list[dict] = []

    # 2. Top-level checks
    findings.extend(_check_top_level(wf))

    # 3. Permissions (top-level)
    if "permissions" in wf:
        findings.extend(_check_permissions(wf["permissions"], "permissions"))

    # 4. Jobs
    jobs = wf.get("jobs") or {}
    if isinstance(jobs, dict):
        all_job_ids = set(jobs.keys())
        for job_id, job in jobs.items():
            findings.extend(_check_job(str(job_id), job, all_job_ids))
        findings.extend(_check_cycles(jobs))

    # 5. Secrets without permissions
    findings.extend(_check_secrets_without_permissions(wf))

    errors   = sum(1 for f in findings if f["level"] == "error")
    warnings = sum(1 for f in findings if f["level"] == "warning")

    return {
        "file":     filename,
        "valid":    errors == 0,
        "errors":   errors,
        "warnings": warnings,
        "findings": findings,
    }


# ── run() ─────────────────────────────────────────────────────────────────────

def run(
    *,
    path: str = ".github/workflows",
    file: str | None = None,
    cwd:  str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if not _HAS_YAML:
            return ForgeResult.failure(
                TOOL, ["pyyaml not installed"], t.elapsed_ms,
                suggestion="pip install pyyaml  or  add pyyaml to [project.optional-dependencies]",
            )

        base = Path(cwd or ".").resolve()
        targets: list[Path] = []

        if file:
            p = Path(file) if Path(file).is_absolute() else base / file
            if not p.exists():
                return ForgeResult.failure(TOOL, [f"File not found: {p}"], t.elapsed_ms)
            targets = [p]
        else:
            scan_dir = Path(path) if Path(path).is_absolute() else base / path
            if scan_dir.is_file():
                targets = [scan_dir]
            elif scan_dir.is_dir():
                targets = sorted(scan_dir.glob("*.yml")) + sorted(scan_dir.glob("*.yaml"))
                if not targets:
                    return ForgeResult.failure(
                        TOOL, [f"No .yml/.yaml files found in {scan_dir}"], t.elapsed_ms,
                        suggestion="Pass --file to validate a specific workflow",
                    )
            else:
                return ForgeResult.failure(
                    TOOL, [f"Path not found: {scan_dir}"], t.elapsed_ms,
                    suggestion="Default path is .github/workflows — pass --path or --file",
                )

        results = [
            _validate_workflow(p.read_text(encoding="utf-8"), str(p.relative_to(base)))
            for p in targets
        ]

        total_errors   = sum(r["errors"]   for r in results)
        total_warnings = sum(r["warnings"] for r in results)
        all_valid      = all(r["valid"]    for r in results)

        data = {
            "valid":          all_valid,
            "files_checked":  len(results),
            "total_errors":   total_errors,
            "total_warnings": total_warnings,
            "results":        results,
        }

        if not all_valid:
            return ForgeResult(
                ok=False,
                tool=TOOL,
                data=data,
                errors=[f"{total_errors} error(s) in {sum(1 for r in results if not r['valid'])} file(s)"],
                duration_ms=t.elapsed_ms,
            )

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".github/workflows",
                   help="Directory to scan for workflow files (default: .github/workflows)")
    p.add_argument("--file", "-f", default=None,
                   help="Validate a single workflow file")
    p.add_argument("--cwd", default=None, help="Working directory")


if __name__ == "__main__":
    make_cli(TOOL, "Validate GitHub Actions workflow YAML files", run, _add_args)
