"""Domain resources and prompts shared by split MCP servers."""
from __future__ import annotations

import importlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from forgetools._forge_cli import REGISTRY
from forgetools.mcp_prompts import PROMPTS


def _run_tool(key: str, **kwargs) -> dict[str, Any]:
    mod = importlib.import_module(REGISTRY[key])
    return mod.run(**kwargs).to_dict()


def _read_repo_doc(relative_path: str) -> str:
    path = Path(__file__).resolve().parent.parent / relative_path
    return path.read_text(encoding="utf-8")


def _json_error(exc: Exception) -> str:
    return json.dumps({"ok": False, "error": str(exc)})


PROMPTS_BY_DOMAIN: dict[str, tuple[str, ...]] = {
    "file": ("new_tool_scaffold", "gitignore_setup"),
    "git": (
        "code_review",
        "release_workflow",
        "debug_ci_failure",
        "parallel_worktree_workflow",
        "multi_repo_health",
        "conventional_commit",
        "commit_amend",
        "commit_history_cleanup",
        "worktree_feature",
        "worktree_hotfix",
        "pr_create_flow",
        "pr_stack",
        "best_practice_commits",
    ),
    "specnative": ("start_feature", "repo_health_check", "specnative_workflow"),
    "java": ("java_project_analysis", "maven_dependency_research", "security_audit"),
    "build": ("dependency_upgrade", "go_project_analysis"),
    "data": ("database_migration",),
    "containers": ("docker_debug", "k8s_deploy"),
    "docs": ("api_design",),
    "linux": ("bug_investigation", "performance_analysis"),
    "quality": ("code_review", "security_audit", "repo_health_check"),
    "office": ("api_design",),
    "python": ("new_tool_scaffold", "dependency_upgrade"),
    "frontend": ("bug_investigation", "performance_analysis"),
    "observability": ("bug_investigation", "performance_analysis"),
    "cloud": ("repo_health_check",),
    "podman": ("docker_debug",),
    "ai": ("performance_analysis",),
    "release": ("release_workflow",),
    "deps": ("dependency_upgrade", "maven_dependency_research"),
}


def register_domain_prompts(server: FastMCP, domain: str) -> None:
    for name in PROMPTS_BY_DOMAIN.get(domain, ()):
        server.prompt()(PROMPTS[name])


def register_domain_resources(server: FastMCP, domain: str) -> None:
    if domain == "git":
        _register_git_resources(server)
    elif domain == "specnative":
        _register_specnative_resources(server)
    elif domain == "linux":
        _register_linux_resources(server)
    elif domain == "file":
        _register_file_resources(server)
    elif domain == "java":
        _register_java_resources(server)
    elif domain == "containers":
        _register_container_resources(server)
    elif domain == "data":
        _register_data_resources(server)
    elif domain == "podman":
        _register_podman_resources(server)
    elif domain == "python":
        _register_python_resources(server)
    elif domain == "quality":
        _register_quality_resources(server)
    elif domain == "office":
        _register_office_resources(server)


def _register_git_resources(server: FastMCP) -> None:
    @server.resource("forge://git/status")
    def resource_git_status() -> str:
        """Current git working-tree status of the cwd repository."""
        try:
            return json.dumps(_run_tool("git status"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://git/log")
    def resource_git_log() -> str:
        """Last 20 commits of the cwd repository."""
        try:
            return json.dumps(_run_tool("git log", limit=20), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://git/worktrees")
    def resource_git_worktrees() -> str:
        """Active git worktrees for the cwd repository."""
        try:
            return json.dumps(_run_tool("git worktree", action="list"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://git/branches")
    def resource_git_branches() -> str:
        """All branches with ahead/behind tracking information for the cwd repository."""
        try:
            return json.dumps(_run_tool("git branch", action="list"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://gh/open-prs")
    def resource_gh_open_prs() -> str:
        """Open pull requests for the current repository."""
        try:
            return json.dumps(_run_tool("gh pr-list", state="open"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://gh/ci-status")
    def resource_gh_ci_status() -> str:
        """Latest GitHub Actions workflow runs for the current repository."""
        try:
            return json.dumps(_run_tool("gh actions", limit=3), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://gh/repo-status")
    def resource_gh_repo_status() -> str:
        """Aggregated GitHub repository status: PRs, checks, reviewers, issues, and branches."""
        try:
            return json.dumps(_run_tool("gh repo-status"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://git/parallel-workflow")
    def resource_git_parallel_workflow() -> str:
        """Status of active parallel worktree workflow sessions in the cwd repo."""
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=os.getcwd(),
            )
            if result.returncode != 0:
                return json.dumps({"ok": False, "error": "Not a git repository"})
            return json.dumps({"ok": True, "worktrees_porcelain": result.stdout}, indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://git/worktree-guide")
    def resource_git_worktree_guide() -> str:
        """Reference guide for git worktree concepts and the parallel workflow engine."""
        return """# Git Parallel Worktree Workflow

Use `git_worktree_workflow` with actions in this order:

1. plan
2. init
3. status
4. sync
5. integrate
6. finalize
7. abort

Naming conventions:
- integration branch: `{prefix}/{session}-integration`
- task branch: `{prefix}/{session}-{task}`
- worktree path: `{wt_base}/{session}-{task}`

Merge readiness:
- Use `git_worktree_merge_plan` before integrating tasks.
- Dirty task worktrees must be committed or stashed before integration.
- Tasks behind the integration branch should run `sync` first.
- Integrate one task at a time, then run tests from the integration branch.
"""

    @server.resource("forge://git/pr-workflows")
    def resource_git_pr_workflows() -> str:
        """Reference guide for stacked PR and backport planning tools."""
        return """# Git PR Workflows

Stacked PRs:
- Use `git_stack_plan(tasks="api,ui,docs", base="main")`.
- Create branches in the returned order.
- Each PR targets the previous stack branch.

Backports:
- Use `git_backport_plan(commits="abc123,def456", targets="release/1.2,release/1.3")`.
- Cherry-pick with `-x`, run target branch tests, and open one PR per target branch.

Preflight:
- Use `git_preflight(action="push")` before pushing.
- Use `git_preflight(action="merge", branch="main")` before merging into protected branches.
"""


def _register_podman_resources(server: FastMCP) -> None:
    @server.resource("forge://podman/policy/bastion-ports")
    def resource_podman_policy() -> str:
        """Bastion Podman port allocation policy."""
        return _read_repo_doc("docs/policies/podman-port-allocation-bastion.md")

    @server.resource("forge://podman/ports")
    def resource_podman_ports() -> str:
        """Occupied and available Podman published ports grouped by policy range."""
        try:
            return json.dumps(_run_tool("podman ports"), indent=2)
        except Exception as exc:
            return _json_error(exc)


def _register_python_resources(server: FastMCP) -> None:
    @server.resource("forge://python/standards/uv")
    def resource_python_uv() -> str:
        """Local Python/uv workflow standards."""
        return """# Python/uv Standards

- Use `uv` for virtualenv, dependency installation, locking, and command execution.
- Prefer `uv sync` for reproducible environments.
- Prefer `uv run pytest`, `uv run ruff check`, and `uv run mypy` when project config exists.
- Keep per-MCP packaging in its own `mcps/<domain>/pyproject.toml`.
"""


def _register_quality_resources(server: FastMCP) -> None:
    @server.resource("forge://quality/gates")
    def resource_quality_gates() -> str:
        """Recommended quality gates before commit or release."""
        return """# Quality Gates

- Lint must pass for touched language/toolchain.
- Tests covering changed behavior must pass.
- Coverage regressions must be reviewed.
- Security scanners must have no critical/high findings unless explicitly accepted.
- Secret scan must be clean before pushing.
"""


def _register_office_resources(server: FastMCP) -> None:
    @server.resource("forge://office/report-workflow")
    def resource_office_report_workflow() -> str:
        """Recommended workflow for generating business reports with mcp-office."""
        return """# Office Report Workflow

1. Generate source content in Markdown or HTML.
2. Use `office_docx_create` when reviewers need editable documents.
3. Use `office_pdf_create` when the artifact must be immutable.
4. Use `office_table_report` for CSV/XLSX appendices.
5. Use `office_pdf_append_tables` to attach tabular appendices to a PDF.
6. Use `office_pdf_metadata`, `office_pdf_text`, and `office_pdf_images` for validation/extraction.
7. Use `office_pdf_stamp` for visible draft/confidential/review stamps.
"""

    @server.resource("forge://office/dependency-policy")
    def resource_office_dependency_policy() -> str:
        """Office MCP dependency policy and optional local tool expectations."""
        return """# Office Dependency Policy

Python dependencies are scoped to `mcps/office/pyproject.toml`:

- `reportlab` for PDF generation and stamping overlays.
- `python-docx` for DOCX generation.
- `pypdf` for PDF merge/metadata/text/images/stamping composition.
- `openpyxl` for XLSX table ingestion.

External CLIs such as `pdfunite` or `qpdf` may still be used by `office_pdf_merge` when available.
"""

def _register_specnative_resources(server: FastMCP) -> None:
    specnative_docs = (
        "product",
        "architecture",
        "stack",
        "conventions",
        "commands",
        "decisions",
        "roadmap",
        "traceability",
        "agents",
        "schema",
        "ci",
        "cd",
        "spec",
    )

    @server.resource("forge://context/repo")
    def resource_context_repo() -> str:
        """Repository size, language breakdown, and git metadata for cwd."""
        try:
            return json.dumps(_run_tool("context repo-size"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://context/summary")
    def resource_context_summary() -> str:
        """AI-readable codebase summary: structure, languages, and key patterns."""
        try:
            return json.dumps(_run_tool("context summarize"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://specnative/{document}")
    def resource_specnative(document: str) -> str:
        """Read a SpecNative context document from the current repository."""
        if document not in specnative_docs:
            return json.dumps({"ok": False, "error": f"Unknown document '{document}'", "valid": list(specnative_docs)})
        try:
            return json.dumps(_run_tool("specnative context", action="read", document=document), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://specnative/status")
    def resource_specnative_status() -> str:
        """All SpecNative specs with their states and task counts for the current repo."""
        try:
            return json.dumps(_run_tool("specnative status", action="status"), indent=2)
        except Exception as exc:
            return _json_error(exc)


def _register_linux_resources(server: FastMCP) -> None:
    @server.resource("forge://diag/health")
    def resource_diag_health() -> str:
        """System health: availability of required development tools."""
        try:
            return json.dumps(_run_tool("diag health"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://diag/env")
    def resource_diag_env() -> str:
        """Environment variables relevant to development tools."""
        try:
            return json.dumps(_run_tool("diag env"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://process/listening")
    def resource_process_listening() -> str:
        """Snapshot of all listening ports on the local machine."""
        try:
            return json.dumps(_run_tool("process ports", action="listen"), indent=2)
        except Exception as exc:
            return _json_error(exc)


def _register_file_resources(server: FastMCP) -> None:
    @server.resource("forge://config/gitignore")
    def resource_config_gitignore() -> str:
        """Current .gitignore content and missing preset analysis."""
        try:
            from forgetools.config.gitignore import _PRESETS

            gitignore_path = os.path.join(os.getcwd(), ".gitignore")
            if not os.path.exists(gitignore_path):
                return json.dumps({"ok": False, "path": gitignore_path, "error": ".gitignore not found"}, indent=2)
            with open(gitignore_path, encoding="utf-8") as f:
                content = f.read()
            existing = {ln.strip() for ln in content.splitlines()}
            analysis = {
                key: [ln for ln in cfg["lines"] if ln not in existing]
                for key, cfg in _PRESETS.items()
            }
            analysis = {key: missing for key, missing in analysis.items() if missing}
            return json.dumps(
                {"ok": True, "path": gitignore_path, "content": content, "missing_patterns": analysis, "fully_covered": not analysis},
                indent=2,
            )
        except Exception as exc:
            return _json_error(exc)


def _register_java_resources(server: FastMCP) -> None:
    @server.resource("forge://java/maven-central/{coords}")
    def resource_maven_central(coords: str) -> str:
        """Maven Central info for an artifact given groupId:artifactId[:version]."""
        try:
            parts = coords.split(":", 2)
            if len(parts) < 2:
                return json.dumps({"ok": False, "error": "coords must be groupId:artifactId[:version]"})
            group_id, artifact_id = parts[0], parts[1]
            version = parts[2] if len(parts) > 2 else None
            if version:
                data = _run_tool("java maven-central", action="checksums", group_id=group_id, artifact_id=artifact_id, version=version)
            else:
                data = _run_tool("java maven-central", action="latest", group_id=group_id, artifact_id=artifact_id)
            return json.dumps(data, indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://test/coverage")
    def resource_test_coverage() -> str:
        """Latest test coverage summary for the cwd project."""
        try:
            return json.dumps(_run_tool("test coverage-report", action="summary"), indent=2)
        except Exception as exc:
            return _json_error(exc)


def _register_container_resources(server: FastMCP) -> None:
    @server.resource("forge://policy/podman-ports-bastion")
    def resource_policy_podman_ports_bastion() -> str:
        """Mandatory Podman port allocation policy for the bastion host."""
        try:
            return _read_repo_doc("docs/policies/podman-port-allocation-bastion.md")
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://docker/containers")
    def resource_docker_containers() -> str:
        """Running Docker containers snapshot."""
        try:
            return json.dumps(_run_tool("docker ps"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://k8s/pods")
    def resource_k8s_pods() -> str:
        """Current Kubernetes pod status across all namespaces."""
        try:
            return json.dumps(_run_tool("k8s pods"), indent=2)
        except Exception as exc:
            return _json_error(exc)


def _register_data_resources(server: FastMCP) -> None:
    @server.resource("forge://db/schema/{database}")
    def resource_db_schema(database: str) -> str:
        """Database schema snapshot for the given database name."""
        try:
            return json.dumps(_run_tool("db schema", action="tables", database=database), indent=2)
        except Exception as exc:
            return _json_error(exc)
