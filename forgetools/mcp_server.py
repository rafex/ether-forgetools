"""forge-mcp — FastMCP server: tools + resources + prompts.

TOOLS    — every REGISTRY entry becomes an MCP tool (existing behaviour)
RESOURCES — read-only data snapshots consumed without a tool call:
              forge://catalog                  full tool list + docstrings
              forge://git/status               current repo working-tree state
              forge://git/log                  last 20 commits
              forge://git/worktrees            active worktrees
              forge://context/repo             repo size + language breakdown
              forge://diag/health              system health (tools available)
              forge://diag/env                 environment variables (filtered)
              forge://specnative/{document}    any SpecNative context doc
PROMPTS   — workflow starters that sequence tools for common tasks:
              start_feature                    worktree + spec + plan
              code_review                      diff + context + pr
              security_audit                   owasp + spotbugs + eslint + secrets
              release_workflow                 changelog + tag + gh release
              debug_ci_failure                 actions logs + failed jobs
              java_project_analysis            maven + jdt + coverage + format
              repo_health_check                status + size + lint + tests
              specnative_workflow              spec-first full lifecycle
              multi_repo_health                side-by-side repos health check
              new_tool_scaffold                scaffold a new forgetools module

Usage:
    forge-mcp                  # stdio (default, for Claude Code / opencode)
    python -m forgetools.mcp_server
"""
from __future__ import annotations

import functools
import importlib
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from forgetools._forge_cli import REGISTRY

# ── Server ────────────────────────────────────────────────────────────────────

server = FastMCP("forgetools")


# ─────────────────────────────────────────────────────────────────────────────
# TOOLS  (existing behaviour — every REGISTRY entry)
# ─────────────────────────────────────────────────────────────────────────────

def _wrap(fn):
    """Return dict instead of ForgeResult, preserve signature for schema gen."""
    @functools.wraps(fn)
    def wrapped(**kwargs):
        result = fn(**kwargs)
        return result.to_dict()
    wrapped.__signature__ = inspect.signature(fn)
    return wrapped


for _key, _module_path in REGISTRY.items():
    _mod  = importlib.import_module(_module_path)
    _run  = getattr(_mod, "run")
    _name = _key.replace(" ", "_").replace("-", "_")
    server.tool(name=_name)(_wrap(_run))


# ─────────────────────────────────────────────────────────────────────────────
# RESOURCES
# ─────────────────────────────────────────────────────────────────────────────

def _run_tool(key: str, **kwargs) -> dict[str, Any]:
    """Call a registered tool's run() and return its dict representation."""
    mod  = importlib.import_module(REGISTRY[key])
    res  = mod.run(**kwargs)
    return res.to_dict()


def _git(*args: str, cwd: str | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True,
            cwd=cwd or os.getcwd(), timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ── forge://catalog ───────────────────────────────────────────────────────────

@server.resource("forge://catalog")
def resource_catalog() -> str:
    """Complete list of forgetools tools with their descriptions and parameters."""
    lines = ["# Forgetools Catalog\n",
             f"Total tools: {len(REGISTRY)}\n"]

    current_cat = None
    for key, module_path in REGISTRY.items():
        cat = key.split(" ", 1)[0]
        if cat != current_cat:
            lines.append(f"\n## {cat.upper()}")
            current_cat = cat
        try:
            mod      = importlib.import_module(module_path)
            docstring = (inspect.getdoc(mod.run) or "").split("\n")[0]
            sig      = str(inspect.signature(mod.run))
        except Exception:
            docstring = ""
            sig       = "()"
        tool_name = key.replace(" ", "_").replace("-", "_")
        lines.append(f"\n### `{tool_name}`")
        lines.append(f"- **forge key**: `forge {key}`")
        if docstring:
            lines.append(f"- **description**: {docstring}")
        lines.append(f"- **signature**: `run{sig}`")

    return "\n".join(lines)


# ── forge://git/status ────────────────────────────────────────────────────────

@server.resource("forge://git/status")
def resource_git_status() -> str:
    """Current git working-tree status of the cwd repository."""
    try:
        data = _run_tool("git status")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://git/log ───────────────────────────────────────────────────────────

@server.resource("forge://git/log")
def resource_git_log() -> str:
    """Last 20 commits of the cwd repository."""
    try:
        data = _run_tool("git log", limit=20)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://git/worktrees ─────────────────────────────────────────────────────

@server.resource("forge://git/worktrees")
def resource_git_worktrees() -> str:
    """Active git worktrees for the cwd repository."""
    try:
        data = _run_tool("git worktree", action="list")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://context/repo ──────────────────────────────────────────────────────

@server.resource("forge://context/repo")
def resource_context_repo() -> str:
    """Repository size, language breakdown, and git metadata for cwd."""
    try:
        data = _run_tool("context repo-size")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://diag/health ───────────────────────────────────────────────────────

@server.resource("forge://diag/health")
def resource_diag_health() -> str:
    """System health: availability of git, gh, mvn, docker, node, go, etc."""
    try:
        data = _run_tool("diag health")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://diag/env ──────────────────────────────────────────────────────────

@server.resource("forge://diag/env")
def resource_diag_env() -> str:
    """Environment variables relevant to development tools (filtered, no secrets)."""
    try:
        data = _run_tool("diag env")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://specnative/{document} ─────────────────────────────────────────────

_SPECNATIVE_DOCS = (
    "product", "architecture", "stack", "conventions",
    "commands", "decisions", "roadmap", "traceability",
    "agents", "schema", "ci", "cd", "spec",
)


@server.resource("forge://specnative/{document}")
def resource_specnative(document: str) -> str:
    """Read a SpecNative context document from the current repository.

    Valid document names:
      product | architecture | stack | conventions | commands |
      decisions | roadmap | traceability | agents | schema | ci | cd | spec
    """
    if document not in _SPECNATIVE_DOCS:
        return json.dumps({
            "ok": False,
            "error": f"Unknown document '{document}'",
            "valid": list(_SPECNATIVE_DOCS),
        })
    try:
        data = _run_tool("specnative context", action="read", document=document)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://specnative/status ────────────────────────────────────────────────

@server.resource("forge://specnative/status")
def resource_specnative_status() -> str:
    """All SpecNative specs with their states and task counts for the current repo."""
    try:
        data = _run_tool("specnative status", action="status")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

@server.prompt()
def start_feature(initiative: str, problem: str) -> str:
    """Start a new feature using git worktree isolation + SpecNative spec scaffold.

    Args:
        initiative: Short hyphenated name for the feature (e.g. 'user-auth')
        problem:    One-sentence description of the problem being solved
    """
    return f"""\
# Start Feature: `{initiative}`

**Problem:** {problem}

You are starting a new feature in a spec-first, isolated workspace.
Follow these steps **in order**:

## 1. Create isolated workspace
```
git_worktree(action="add", path="../worktrees/{initiative}", branch="{initiative}", new_branch=True)
```

## 2. Scaffold the spec (preview first, then write)
```
specnative_initiative(action="start", initiative="{initiative}", problem="{problem}", owner="<your-name>")
# Review the preview, then:
specnative_initiative(action="start", initiative="{initiative}", problem="{problem}", owner="<your-name>", write=True)
```

## 3. Read project context before planning
```
specnative_context(action="read", document="architecture")
specnative_context(action="read", document="conventions")
specnative_context(action="read", document="stack")
context_repo_size()
```

## 4. Derive tasks from spec acceptance criteria
```
specnative_initiative(action="plan", initiative="{initiative}")
# Review the preview, then:
specnative_initiative(action="plan", initiative="{initiative}", write=True)
```

## 5. Begin implementation
```
specnative_initiative(action="implement", initiative="{initiative}")
# Read the returned target_tasks, spec_summary, and conventions before coding
```

## 6. Track progress
After completing each task, update its state:
```
specnative_initiative(action="state", initiative="{initiative}", task_id="TASK-...", state="done", write=True)
```

## 7. Review and close
```
specnative_initiative(action="review", initiative="{initiative}")
# When ready_to_close = true:
specnative_initiative(action="close", initiative="{initiative}", write=True)
```
"""


@server.prompt()
def code_review(pr_number: int, depth: str = "standard") -> str:
    """Review a pull request: diff, context, checks, and review comments.

    Args:
        pr_number: GitHub PR number to review
        depth:     'quick' (diff only) | 'standard' (diff + checks) | 'deep' (full analysis)
    """
    steps = f"""\
# Code Review: PR #{pr_number}

## 1. Get PR overview
```
gh_pr_review(number={pr_number})
```

## 2. See files changed
```
gh_pr_diff(action="files", number={pr_number})
```

## 3. Read the diff
```
gh_pr_diff(action="diff", number={pr_number})
```
"""
    if depth in ("standard", "deep"):
        steps += f"""
## 4. Check CI status
```
gh_pr_merge(action="check", number={pr_number})
```

## 5. Read project conventions
```
specnative_context(action="read", document="conventions")
```
"""
    if depth == "deep":
        steps += f"""
## 6. Summarize context of changed files
```
context_diff_summary()
```

## 7. Check for secrets in diff
```
secrets_scan()
```

## 8. Run linting on changed files
```
lint_eslint()   # for JS/TS
lint_pylint()   # for Python
lint_checkstyle()  # for Java
```

## 9. Review decisions for conflicts
```
specnative_context(action="decisions")
```
"""
    steps += f"""
## Final step: Add review comment or merge
```
# To request changes:
gh_issue_view(action="comments", number={pr_number})

# To merge when approved:
gh_pr_merge(action="merge", number={pr_number}, method="squash")
```
"""
    return steps


@server.prompt()
def security_audit(target_dir: str = ".", scope: str = "full") -> str:
    """Run a comprehensive security audit on the codebase.

    Args:
        target_dir: Directory to audit (default: current directory)
        scope:      'deps' (dependencies only) | 'code' (static analysis) | 'full' (both)
    """
    steps = f"# Security Audit: `{target_dir}`\n\n"

    if scope in ("deps", "full"):
        steps += """\
## 1. Scan dependencies for CVEs (OWASP)
```
security_owasp(action="scan", cwd="{target_dir}")
# Parse results:
security_owasp(action="report", cwd="{target_dir}")
```

## 2. Audit npm dependencies
```
npm_audit(cwd="{target_dir}")
```
""".format(target_dir=target_dir)

    if scope in ("code", "full"):
        steps += """\
## 3. Java static analysis (SpotBugs + Find Security Bugs)
```
security_spotbugs(action="scan", cwd="{target_dir}", security_only=True)
```

## 4. JavaScript/TypeScript static analysis (ESLint security)
```
security_eslint(action="scan", cwd="{target_dir}")
```

## 5. Scan for secrets and credentials in code
```
secrets_scan(cwd="{target_dir}")
```

## 6. Validate GitHub Actions workflows
```
gh_actions_validate(cwd="{target_dir}")
```
""".format(target_dir=target_dir)

    steps += """\
## Summary
After running the above, check:
- `ok: false` results indicate findings requiring action
- CRITICAL/HIGH CVEs block releases
- Security bug prefixes: SQL_INJECTION, XSS_, PATH_TRAVERSAL, HARD_CODE_PASSWORD
- Built-in rules: no-eval, no-new-func, no-implied-eval
"""
    return steps


@server.prompt()
def release_workflow(version: str, repo: str = "", branch: str = "main") -> str:
    """Prepare and publish a new release.

    Args:
        version: Semantic version string, e.g. 'v2.1.0'
        repo:    GitHub 'owner/repo' (leave empty to use current repo)
        branch:  Branch to release from (default: main)
    """
    repo_flag = f", repo='{repo}'" if repo else ""
    return f"""\
# Release Workflow: `{version}`

## 1. Verify repo is clean
```
git_status()
git_multi_repo(action="status")
```

## 2. Check all tests pass
```
java_maven(goal="verify")       # Java projects
go_test()                       # Go projects
npm_run(script="test")          # JS/TS projects
```

## 3. Run security scan
```
security_owasp(action="scan")
secrets_scan()
```

## 4. Generate / update changelog
```
docs_changelog(action="generate", version="{version}", output="CHANGELOG.md")
```

## 5. Create release tag
```
git_tag(action="create", name="{version}", message="Release {version}")
```

## 6. Create GitHub release with auto-generated notes
```
gh_release(tag="{version}", title="Release {version}"{repo_flag})
```

## 7. Verify release assets
```
gh_api_releases(action="get", slug="<owner>/<repo>", tag="{version}")
```

## 8. Update traceability (SpecNative projects)
```
specnative_initiative(action="close", initiative="release-{version}", write=True)
```
"""


@server.prompt()
def debug_ci_failure(run_id: int) -> str:
    """Diagnose and fix a failing GitHub Actions workflow run.

    Args:
        run_id: The workflow run ID from GitHub Actions
    """
    return f"""\
# Debug CI Failure: Run #{run_id}

## 1. Get job overview
```
gh_actions_logs(action="jobs", run_id={run_id})
```

## 2. Read failed steps only
```
gh_actions_logs(action="failed", run_id={run_id})
```

## 3. Tail the full log (last 200 lines)
```
gh_actions_logs(action="tail", run_id={run_id}, lines=200)
```

## 4. Validate the workflow YAML
```
gh_actions_validate()
```

## 5. Check environment and tool availability
```
diag_health()
diag_env()
```

## 6. Look for related issues
```
gh_api_search(action="issues", query="CI failure run {run_id}", repo="<owner>/<repo>")
```

## 7. Re-run failed jobs only (after fix)
```
gh_actions_trigger(action="rerun", run_id={run_id}, failed_only=True)
```

## 8. Watch the re-run
```
gh_actions_trigger(action="watch", run_id={run_id}, timeout=300)
```
"""


@server.prompt()
def java_project_analysis(project_dir: str = ".") -> str:
    """Comprehensive analysis of a Java/Maven project.

    Args:
        project_dir: Root directory of the Java project (default: cwd)
    """
    return f"""\
# Java Project Analysis: `{project_dir}`

## 1. Discover Maven module structure
```
java_maven_modules(action="summary", dir="{project_dir}", pattern="*")
java_maven_modules(action="list",    dir="{project_dir}")
```

## 2. Locate Java Language Server (eclipse.jdt.ls)
```
java_jdt(action="locate")
```

## 3. Check code formatting
```
java_format(action="check", path="{project_dir}")
```

## 4. Run build
```
java_maven(goal="compile -DskipTests", cwd="{project_dir}")
```

## 5. Run tests and collect coverage
```
java_maven(goal="verify", cwd="{project_dir}")
test_coverage_report(action="report", cwd="{project_dir}")
test_coverage_report(action="check",  cwd="{project_dir}", min=80)
```

## 6. Static security analysis
```
security_spotbugs(action="scan", cwd="{project_dir}", security_only=True)
security_owasp(action="scan",    cwd="{project_dir}")
```

## 7. Lint (Checkstyle)
```
lint_checkstyle(cwd="{project_dir}")
```

## 8. Parse any stacktraces in logs
```
java_stacktrace(cwd="{project_dir}")
```
"""


@server.prompt()
def repo_health_check(repo_dir: str = ".") -> str:
    """Full health dashboard for a repository.

    Args:
        repo_dir: Repository root directory (default: cwd)
    """
    return f"""\
# Repository Health Check: `{repo_dir}`

## 1. Size and language breakdown
```
context_repo_size(cwd="{repo_dir}")
```

## 2. Git state
```
git_status(cwd="{repo_dir}")
git_worktree(action="list", cwd="{repo_dir}")
```

## 3. Recent activity
```
git_log(limit=10, cwd="{repo_dir}")
context_diff_summary(cwd="{repo_dir}")
```

## 4. Open PRs and issues
```
gh_pr_list(state="open")
gh_issue_list(state="open")
```

## 5. CI status (last 5 runs)
```
gh_actions(limit=5, cwd="{repo_dir}")
```

## 6. Security
```
secrets_scan(cwd="{repo_dir}")
gh_actions_validate(cwd="{repo_dir}")
```

## 7. Code quality
```
lint_eslint(cwd="{repo_dir}")    # JS/TS
lint_pylint(cwd="{repo_dir}")    # Python
lint_checkstyle(cwd="{repo_dir}") # Java
```

## 8. Test coverage
```
test_coverage_report(action="find", cwd="{repo_dir}")
test_coverage_report(action="summary", cwd="{repo_dir}")
```

## 9. Dependencies
```
npm_audit(cwd="{repo_dir}")
security_owasp(action="find", cwd="{repo_dir}")
```

## 10. SpecNative compliance (if applicable)
```
specnative_status(action="validate", repo="{repo_dir}")
specnative_status(action="status",   repo="{repo_dir}")
```
"""


@server.prompt()
def specnative_workflow(initiative: str, action: str = "status") -> str:
    """Full SpecNative spec-first development workflow guide.

    Args:
        initiative: Initiative name (e.g. 'user-auth', 'payment-api')
        action:     'status' | 'start' | 'implement' | 'review' | 'close'
    """
    if action == "status":
        return f"""\
# SpecNative Status: `{initiative}`

## Check repository health
```
specnative_status(action="validate")
specnative_status(action="status")
specnative_status(action="list-specs")
```

## Read spec
```
specnative_context(action="read-spec", initiative="{initiative}")
```

## See tasks
```
specnative_context(action="list-tasks", initiative="{initiative}")
```

## Read relevant decisions
```
specnative_context(action="decisions")
```
"""

    if action == "start":
        return f"""\
# SpecNative Start: `{initiative}`

## 1. Read existing context first
```
specnative_context(action="read", document="product")
specnative_context(action="read", document="roadmap")
specnative_context(action="read", document="decisions")
```

## 2. Scaffold spec
```
specnative_initiative(action="start", initiative="{initiative}", problem="<describe the problem>")
# Review output, then:
specnative_initiative(action="start", initiative="{initiative}", problem="<describe the problem>", write=True)
```

## 3. Scaffold tasks
```
specnative_initiative(action="plan", initiative="{initiative}")
specnative_initiative(action="plan", initiative="{initiative}", write=True)
```
"""

    if action == "implement":
        return f"""\
# SpecNative Implement: `{initiative}`

## 1. Load implementation context
```
specnative_initiative(action="implement", initiative="{initiative}")
```
The result contains: target_tasks, spec_summary, conventions, architecture, stack.

## 2. For each task, update state to in-progress
```
specnative_initiative(action="state", initiative="{initiative}", task_id="TASK-...", state="in-progress", write=True)
```

## 3. Check relevant code
```
search_grep(pattern="<related class or function>")
fs_find_by_type(extensions=".java,.py,.ts")
```

## 4. After completing a task
```
specnative_initiative(action="state", initiative="{initiative}", task_id="TASK-...", state="done", write=True)
```
"""

    if action == "review":
        return f"""\
# SpecNative Review: `{initiative}`

## 1. Check all tasks done
```
specnative_initiative(action="review", initiative="{initiative}")
```

## 2. Verify tests pass
```
java_maven(goal="verify")
go_test()
npm_run(script="test")
```

## 3. Security check
```
secrets_scan()
security_spotbugs(action="scan", security_only=True)
```

## 4. Lint
```
lint_checkstyle()
lint_eslint()
lint_pylint()
```
"""

    if action == "close":
        return f"""\
# SpecNative Close: `{initiative}`

## 1. Final review
```
specnative_initiative(action="review", initiative="{initiative}")
```

## 2. Record any new decisions
```
specnative_initiative(
    action="decision",
    initiative="{initiative}",
    title="<decision title>",
    context="<why this decision was needed>",
    decision="<what was decided>",
    consequences="<trade-offs and impacts>"
)
```

## 3. Close the spec
```
specnative_initiative(action="close", initiative="{initiative}")
# Preview looks good? Write it:
specnative_initiative(action="close", initiative="{initiative}", write=True)
```

## 4. Commit and create PR
```
git_commit(action="commit")
gh_pr_create(title="feat({initiative}): ...", body="Closes spec SPEC-...")
```
"""

    return f"Unknown action '{action}'. Use: status | start | implement | review | close"


@server.prompt()
def multi_repo_health(base_dir: str, pattern: str = "*") -> str:
    """Health check for multiple side-by-side git repositories.

    Args:
        base_dir: Parent directory containing the repos
        pattern:  Glob filter for repo names (e.g. 'ether-*')
    """
    return f"""\
# Multi-Repo Health Check

Base directory: `{base_dir}`
Pattern: `{pattern}`

## 1. Fast status (no network)
```
git_multi_repo(action="status", dir="{base_dir}", pattern="{pattern}", no_fetch=True)
```

## 2. Full sync check (with fetch — slower)
```
git_multi_repo(action="check", dir="{base_dir}", pattern="{pattern}")
```

## 3. Summary dashboard
```
git_multi_repo(action="summary", dir="{base_dir}", pattern="{pattern}")
```
The summary shows:
- `dirty`: repos with uncommitted changes
- `out_of_sync`: repos behind/ahead of origin
- `missing_license`: repos without license headers in source files

## 4. Discover Maven modules across all repos
```
java_maven_modules(action="summary", dir="{base_dir}", pattern="{pattern}")
```

## 5. Fix dirty repos
For each repo in `dirty` list:
```
git_status(cwd="{base_dir}/<repo-name>")
git_diff(cwd="{base_dir}/<repo-name>")
```
"""


@server.prompt()
def new_tool_scaffold(tool_name: str, category: str, description: str) -> str:
    """Scaffold a new forgetools module following the ForgeResult pattern.

    Args:
        tool_name:   Short name for the tool (e.g. 'format', 'analyze')
        category:    Category prefix (e.g. 'java', 'git', 'fs')
        description: One-line description of what the tool does
    """
    full_key = f"{category} {tool_name}"
    module   = f"forgetools.{category}.{tool_name.replace('-', '_')}"
    mcp_name = full_key.replace(" ", "_").replace("-", "_")

    return f"""\
# New Tool: `{full_key}`

Module path: `{module}`
MCP name: `{mcp_name}`
Description: {description}

## 1. Generate scaffold
```
# Use the meta-tool to generate the boilerplate:
shell_run(cmd="python3 scripts/new_tool.py --category {category} --name {tool_name} --description '{description}'")
```

## 2. Implement `run()` in `forgetools/{category}/{tool_name.replace('-', '_')}.py`

The file must follow this pattern:
```python
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "{category}.{tool_name.replace('-', '_')}"

def run(*, action: str = "...", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        # ... implementation ...
        return ForgeResult.success(TOOL, {{...}}, t.elapsed_ms)
```

## 3. Register in `forgetools/_forge_cli.py`
Add to REGISTRY:
```python
"{full_key}": "{module}",
```

## 4. Verify
```
config_validate(file="forgetools/_forge_cli.py")
shell_run(cmd="python3 -c \\"import {module}; print('OK')\\"")
```

## 5. Reload MCP
After `git pull`:
Toggle forgetools off → on in `/mcp` to pick up the new tool `{mcp_name}`.
"""


# ── forge://java/maven-central ───────────────────────────────────────────────

@server.resource("forge://java/maven-central/{coords}")
def resource_maven_central(coords: str) -> str:
    """Maven Central info for an artifact given its coordinates.

    coords format: groupId:artifactId  or  groupId:artifactId:version

    Examples:
      forge://java/maven-central/org.springframework.boot:spring-boot-starter-web
      forge://java/maven-central/com.google.guava:guava:33.4.8-jre
    """
    try:
        parts = coords.split(":", 2)
        if len(parts) < 2:
            return json.dumps({"ok": False, "error": "coords must be groupId:artifactId[:version]"})
        g, a = parts[0], parts[1]
        v    = parts[2] if len(parts) > 2 else None

        if v:
            data = _run_tool("java maven-central",
                             action="checksums", group_id=g, artifact_id=a, version=v)
        else:
            data = _run_tool("java maven-central",
                             action="latest", group_id=g, artifact_id=a)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://git/parallel-workflow ────────────────────────────────────────────

@server.resource("forge://git/parallel-workflow")
def resource_git_parallel_workflow() -> str:
    """Status of all active parallel worktree workflow sessions in the cwd repo.

    A parallel workflow session groups N git worktrees under a shared integration
    branch following the naming convention:
      branches: ai/<session>-integration, ai/<session>-<task>
      paths:    ../.claude/worktrees/<session>-<task>

    Returns every session found, with per-worktree dirty/ahead-behind status
    and a readiness indicator showing which tasks are ready to integrate.
    """
    try:
        import subprocess, os

        # discover active worktrees
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=10,
            cwd=os.getcwd(),
        )
        if result.returncode != 0:
            return json.dumps({"ok": False, "error": "Not a git repository"})

        # parse worktrees
        wts: list[dict] = []
        cur: dict = {}
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                if cur:
                    wts.append(cur)
                cur = {"path": line[9:], "branch": None}
            elif line.startswith("branch "):
                cur["branch"] = line[7:].removeprefix("refs/heads/")
        if cur:
            wts.append(cur)

        # group by session (pattern: <prefix>/<session>-<task>)
        import re
        sessions: dict[str, dict] = {}
        for wt in wts:
            br = wt.get("branch") or ""
            m  = re.match(r'^([^/]+)/([^-]+(?:-[^-]+)*?)-(integration|.+)$', br)
            if not m:
                continue
            prefix, session_candidate, suffix = m.group(1), m.group(2), m.group(3)
            # integration branch
            int_m = re.match(r'^([^/]+)/(.+)-integration$', br)
            if int_m:
                session = int_m.group(2).rsplit("-", 0)[0] if "-" not in int_m.group(2) else int_m.group(2)
                # simpler: extract session from "prefix/SESSION-integration"
                session = br.split("/", 1)[1].removesuffix("-integration")
                key = f"{prefix}/{session}"
                sessions.setdefault(key, {
                    "prefix": prefix, "session": session,
                    "integration_wt": None, "task_wts": [],
                })["integration_wt"] = wt
            else:
                task_m = re.match(r'^([^/]+)/(.+)-([^-]+)$', br)
                if task_m:
                    p2  = task_m.group(1)
                    rest = task_m.group(2)
                    task = task_m.group(3)
                    # heuristic: the rightmost segment is the task name
                    key = f"{p2}/{rest}"
                    sessions.setdefault(key, {
                        "prefix": p2, "session": rest,
                        "integration_wt": None, "task_wts": [],
                    })["task_wts"].append({**wt, "task": task})

        # call the tool for proper status if sessions detected
        if sessions:
            all_status = {}
            for key, sess in sessions.items():
                try:
                    data = _run_tool(
                        "git worktree-workflow",
                        action="status",
                        session=sess["session"],
                        branch_prefix=sess["prefix"],
                        base_branch="main",
                    )
                    all_status[key] = data
                except Exception as exc:
                    all_status[key] = {"error": str(exc)}
            return json.dumps({
                "ok": True,
                "session_count": len(sessions),
                "sessions": all_status,
            }, indent=2)

        return json.dumps({
            "ok": True,
            "session_count": 0,
            "sessions": {},
            "message": (
                "No parallel workflow sessions found. "
                "Sessions use naming: ai/<session>-integration, ai/<session>-<task>. "
                "Use the `parallel_worktree_workflow` prompt to start one."
            ),
        }, indent=2)

    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://git/worktree-guide ────────────────────────────────────────────────

@server.resource("forge://git/worktree-guide")
def resource_git_worktree_guide() -> str:
    """Reference guide for git worktree concepts and the parallel workflow engine.

    Returns the naming conventions, available actions, and agent decision rules
    for the git_worktree_workflow tool.
    """
    return """\
# Git Parallel Worktree Workflow — Agent Reference

## What it is
A structured pattern for AI agents to perform multiple independent changes
simultaneously, each in an isolated git worktree, then merge them through
a single integration branch before landing on main.

## Naming conventions
| Concept | Pattern | Example |
|---------|---------|---------|
| Session | short slug | `auth-refactor` |
| Integration branch | `{prefix}/{session}-integration` | `ai/auth-refactor-integration` |
| Task branch | `{prefix}/{session}-{task}` | `ai/auth-refactor-models` |
| Worktree path | `{wt_base}/{session}-{task}` | `../.claude/worktrees/auth-refactor-models` |

Default prefix: `ai`
Default worktree base: `../.claude/worktrees`

## Actions in order
1. **plan**       — preview all branch/path names, conflict check (no writes)
2. **init**       — create integration branch + N worktrees (one per task)
3. **status**     — dirty/clean, ahead/behind for every worktree
4. **sync**       — rebase/merge base_branch into all task worktrees
5. **integrate**  — merge completed task branch → integration branch
6. **finalize**   — merge integration → target branch, clean up worktrees
7. **abort**      — remove all worktrees + delete all session branches

## Agent decision rules
- Always run **plan** first; check `conflicts` list before **init**
- Work in each task's **path** directory (not the main repo)
- After each task is committed, call **integrate --task <name>**
- Call **status** anytime to see which tasks are ready to integrate
- Call **sync** if the base branch has advanced since **init**
- Only call **finalize** when all tasks are integrated (no errors in **integrate**)
- If aborting mid-session, call **abort** to leave the repo clean

## Merge methods
- `merge`  — default; preserves full history, clear audit trail
- `squash` — condenses each task into one commit; cleaner log
- `rebase` — linearises history; use only for local-only branches

## MCP tool name
`git_worktree_workflow`

## Example session
```
git_worktree_workflow(action="plan",   session="auth-refactor", tasks=["models","api","tests"])
git_worktree_workflow(action="init",   session="auth-refactor", tasks=["models","api","tests"])
# ... work in each worktree ...
git_worktree_workflow(action="integrate", session="auth-refactor", task="models")
git_worktree_workflow(action="integrate", session="auth-refactor", task="api")
git_worktree_workflow(action="integrate", session="auth-refactor", task="tests")
git_worktree_workflow(action="finalize",  session="auth-refactor")
```
"""


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT — parallel_worktree_workflow
# ─────────────────────────────────────────────────────────────────────────────

@server.prompt()
def maven_dependency_research(
    query: str,
    project_dir: str = ".",
) -> str:
    """Research Maven Central for a dependency: find, compare, get checksums, and add to POM.

    Args:
        query:       What you're looking for (e.g. 'json serialization', 'jwt library')
        project_dir: Project directory where pom.xml lives (default: cwd)
    """
    return f"""\
# Maven Dependency Research: `{query}`

You are researching Maven Central to find the best library for: **{query}**

## Phase 1 — Discover candidates
```
java_maven_central(action="search", query="{query}", rows=10)
```
From the results, pick the top 2-3 candidates with the most `version_count`
and recent `timestamp`. Note their `group_id` and `artifact_id`.

## Phase 2 — Evaluate each candidate
For each candidate `groupId:artifactId`:
```
# Full details: description, URL, SCM, latest version
java_maven_central(action="info", coords="<groupId>:<artifactId>")

# Version history (check for active maintenance)
java_maven_central(action="versions", coords="<groupId>:<artifactId>", rows=10)

# Get dependency snippets for the latest version
java_maven_central(action="dependency", coords="<groupId>:<artifactId>")
```

## Phase 3 — Verify integrity before adding
Once you have chosen the library:
```
# Get all checksums for the chosen version
java_maven_central(action="checksums", coords="<groupId>:<artifactId>:<version>")

# Optionally review the POM for transitive dependencies
java_maven_central(action="pom", coords="<groupId>:<artifactId>:<version>")
```

## Phase 4 — Check project context
```
# Find the project POM
java_maven_modules(action="list", dir="{project_dir}")

# Check if the dependency is already present
search_grep(pattern="<artifactId>.*</artifactId>", paths="{project_dir}/pom.xml")
```

## Phase 5 — Add to project
The `dependency` action returns ready-to-paste snippets:
- `maven_xml`       → paste inside `<dependencies>` in pom.xml
- `gradle`          → paste in `build.gradle`
- `gradle_kotlin`   → paste in `build.gradle.kts`

After adding:
```
java_maven(goal="dependency:resolve", cwd="{project_dir}")
```

## Decision checklist
- Latest version released in last 12 months? (check `timestamp`)
- More than 10 versions? (indicates stability)
- SCM URL points to active repo? (check `scm_url`)
- No known CVEs? (run `security_owasp` after adding)
- SHA1 matches what the project's security policy requires?
"""


@server.prompt()
def parallel_worktree_workflow(
    session: str,
    tasks: str,
    base_branch: str = "main",
    merge_method: str = "merge",
) -> str:
    """AI-agent guide for parallel git worktree development and integration.

    Generates a step-by-step execution plan an agent follows to:
      1. Create N isolated worktrees (one per task)
      2. Perform independent changes simultaneously
      3. Merge through an integration branch
      4. Land cleanly on the target branch

    Args:
        session:      Short slug for the session (e.g. 'auth-refactor')
        tasks:        Comma-separated task names  (e.g. 'models,api,tests')
        base_branch:  Branch to start from (default: main)
        merge_method: merge | squash | rebase (default: merge)
    """
    task_list  = [t.strip() for t in tasks.split(",") if t.strip()]
    int_branch = f"ai/{session}-integration"
    task_items = "\n".join(
        f"  - `ai/{session}-{t}` → `../.claude/worktrees/{session}-{t}`"
        for t in task_list
    )
    task_status_calls = "\n".join(
        f'git_worktree_workflow(action="integrate", session="{session}", task="{t}", '
        f'merge_method="{merge_method}")'
        for t in task_list
    )

    return f"""\
# Parallel Worktree Workflow: `{session}`

**Tasks:** {", ".join(task_list)}
**Base branch:** `{base_branch}`
**Integration branch:** `{int_branch}`
**Merge method:** `{merge_method}`

You are an AI agent operating in parallel across {len(task_list)} isolated git worktrees.
Follow **every step in order**. Do not skip steps.

---

## Phase 1 — Plan (no writes)

Read the current repo state and preview the topology.

```
# 1a. Read the worktree guide
# Resource: forge://git/worktree-guide

# 1b. Verify repo health
git_status()
git_worktree(action="list")

# 1c. Preview the session — check for conflicts before creating anything
git_worktree_workflow(
    action="plan",
    session="{session}",
    tasks={json.dumps(task_list)},
    base_branch="{base_branch}",
    merge_method="{merge_method}",
)
```

**If `conflicts` list is non-empty** in the plan output:
- A worktree path or branch already exists
- Resolve before continuing (rename, remove, or abort that session)

---

## Phase 2 — Init (creates branches + worktrees)

```
git_worktree_workflow(
    action="init",
    session="{session}",
    tasks={json.dumps(task_list)},
    base_branch="{base_branch}",
)
```

This creates:
{task_items}

**Expected output**: `created` list with {len(task_list)} worktrees + 1 integration branch.
If any errors appear, read them — most are path conflicts or branch-already-exists.

---

## Phase 3 — Parallel implementation

Work independently in each task worktree. **Each task is a separate directory.**
Never commit to `{base_branch}` or `{int_branch}` directly.

For each task `<task>` in [{", ".join(f'"{t}"' for t in task_list)}]:

```
# Check the worktree is clean before starting
git_worktree_workflow(action="status", session="{session}")

# Work in the task's directory:
#   ../.claude/worktrees/{session}-<task>/

# After finishing the task — commit in that worktree:
git_commit(action="commit", cwd="../.claude/worktrees/{session}-<task>")
```

**Rules while working:**
- One worktree = one concern (e.g., `models` only touches the data layer)
- Avoid modifying the same file in two worktrees (causes merge conflicts)
- Commit early and often within the worktree; squash later via `merge_method`

---

## Phase 4 — Sync (if base_branch advanced)

If other changes landed on `{base_branch}` while you were working:

```
git_worktree_workflow(
    action="sync",
    session="{session}",
    base_branch="{base_branch}",
    merge_method="{merge_method}",
)
```

Resolve any conflicts reported in `errors`, then re-run sync.

---

## Phase 5 — Integrate (one task at a time)

After **each** task is committed and clean, integrate it:

```
{task_status_calls}
```

After each call, check `errors`. A non-empty `errors` means a merge conflict:
```
# In the integration worktree or main repo, resolve conflicts:
git_status(cwd="../.claude/worktrees/{session}-integration")   # if it exists
# or:
git_status()   # if integration branch was checked out in the main repo
```

Monitor overall progress:
```
git_worktree_workflow(action="status", session="{session}")
```

`ready_to_integrate` — tasks with commits not yet in integration
`in_progress` — tasks still dirty (uncommitted changes)

---

## Phase 6 — Finalize

When **all** tasks are integrated (`ready_to_integrate` is empty):

```
git_worktree_workflow(
    action="finalize",
    session="{session}",
    target_branch="{base_branch}",
    merge_method="{merge_method}",
    cleanup=True,
)
```

This:
1. Merges `{int_branch}` → `{base_branch}` using `{merge_method}`
2. Removes all task worktrees (`cleanup=True`)
3. Deletes task branches and the integration branch

**After finalize:**
```
git_status()           # verify {base_branch} is clean
git_log(limit=5)       # verify the merge commit appears

# Push to remote:
shell_run(cmd="git push origin {base_branch}")

# Optional: create a PR instead of pushing directly
gh_pr_create(
    title="feat({session}): parallel implementation of {tasks}",
    body="Parallel worktree session `{session}` integrating: {tasks}",
    base="{base_branch}",
)
```

---

## Emergency abort

If something went wrong and you need to clean up:

```
git_worktree_workflow(action="abort", session="{session}")
```

This removes all worktrees and deletes all session branches.
The main repo is returned to the state before `init`.

---

## Quick reference

| Action | When to call |
|--------|-------------|
| `plan` | Before init — sanity check, preview names |
| `init` | Once — creates all worktrees |
| `status` | Anytime — see dirty/ahead-behind |
| `sync` | When `{base_branch}` has new commits |
| `integrate` | After each task is committed |
| `finalize` | When all tasks integrated |
| `abort` | Emergency rollback |
"""


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
