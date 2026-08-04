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
    "specnative": (
        "specnative",
        "capture_backlog",
        "init_project_guided",
        "start_initiative",
        "plan_tasks",
        "implement_task",
        "review_against_spec",
        "handoff",
        "record_decision",
        "close_initiative",
        "start_feature",
        "repo_health_check",
        "specnative_workflow",
        "specnative_handoff",
        "specnative_init_project",
        "specnative_plan_tasks",
        "specnative_implement_task",
        "specnative_close_initiative",
    ),
    "java": ("java_project_analysis", "maven_dependency_research", "security_audit"),
    "build": ("dependency_upgrade", "go_project_analysis", "build_project_scaffold"),
    "data": ("database_migration",),
    "containers": ("docker_debug", "k8s_deploy"),
    "docs": ("api_design",),
    "linux": ("bug_investigation", "performance_analysis", "linux_host_audit"),
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
    elif domain == "build":
        _register_build_resources(server)
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


def _register_build_resources(server: FastMCP) -> None:
    @server.resource("forge://build/standards/structure")
    def resource_build_structure() -> str:
        """Repository build and task-management structure standards."""
        return """# Build and Task Management Structure

Use this layout for repositories that separate construction from daily task execution:

```text
Makefile
Justfile
helpers/
  shell/       # Reusable POSIX shell scripts
  python/      # Python helpers executed with uv
  mk/          # Make include files and build modules
  just/        # Just modules and task recipes
```

Responsibility boundaries:

- `Makefile` is only for construction: compile, package, test gates, generated artifacts, and CI build entry points.
- `Justfile` is the task manager: local development, formatting, migrations, environment setup, and composed workflows.
- `helpers/mk` contains Make modules; those modules may call `helpers/shell` or `helpers/python`.
- `helpers/just` contains Just modules; those modules may call `helpers/shell`, `helpers/python`, or Make build targets.
- `helpers/python` must use the repository's `uv` environment and `pyproject.toml`.
- `Makefile` must never call `Justfile`; dependency direction is `Justfile -> Makefile`, never the reverse.

Prefer one responsibility per helper. Keep recipes thin and put reusable logic in a typed Python or shell helper with structured errors.
"""

    @server.resource("forge://build/standards/python")
    def resource_build_python() -> str:
        """Python construction standards using uv, pip, and wheel."""
        return """# Python Build Standards

## Source of truth

- Keep project metadata and dependencies in `pyproject.toml`.
- Use one `pyproject.toml` per independently installable MCP/domain package.
- Commit `uv.lock` for applications and reproducible development environments when the project policy requires it.

## uv workflow

```bash
uv venv --python 3.13 .venv
uv add <package>
uv lock
uv sync
uv run pytest
uv run ruff check .
uv build
```

Use `uv run` for project commands so the selected environment is explicit. Use `uv pip` only when interoperating with a pip-compatible environment or installing a built artifact:

```bash
uv pip install --python .venv/bin/python -e .
uv pip install --python .venv/bin/python dist/example-*.whl
uv pip compile pyproject.toml -o requirements.txt
```

Avoid raw `pip install` in build recipes. If pip compatibility is required, invoke it through `uv pip` and name the target interpreter.

## wheel artifacts

- Build distributions with `uv build`.
- Treat `dist/*.whl` and `dist/*.tar.gz` as generated artifacts.
- Validate the wheel in a clean environment before publishing.
- Do not mix editable installation behavior with release artifact validation.
"""

    @server.resource("forge://build/standards/java")
    def resource_build_java() -> str:
        """Java construction standards for Maven, Gradle, and Ant."""
        return """# Java Build Standards

## Tool selection

- Maven projects are identified by `pom.xml`; prefer the repository wrapper `./mvnw`.
- Gradle projects are identified by `settings.gradle` or `settings.gradle.kts`; prefer `./gradlew`.
- Ant projects are identified by `build.xml`; use Ant only when the repository is explicitly Ant-based.
- Do not replace Maven or Gradle with Ant for a project that already has a canonical build tool.

## Maven

```bash
./mvnw -B validate
./mvnw -B test
./mvnw -B verify
./mvnw -B package -DskipTests
```

Keep dependency and plugin versions in the POM or governed properties. Use the Maven wrapper and preserve the project Java/toolchain configuration.

## Gradle

```bash
./gradlew tasks
./gradlew test
./gradlew check
./gradlew build
```

Prefer the Gradle wrapper, version catalogs, and convention plugins already present in the repository. Avoid changing global Gradle configuration from a helper.

## Ant

```bash
ant -p
ant clean test
ant dist
```

Use named targets from `build.xml`; do not assume Maven lifecycle names in Ant projects.

## Shared rules

- Build helpers must be reproducible and must not hide tool output or failures.
- Tests are part of the build gate; task-manager recipes may compose build targets but must not duplicate them.
- Generated artifacts belong in the configured build directory and must not be committed unless the repository policy says so.
"""

    @server.resource("forge://build/standards/make-just-boundaries")
    def resource_make_just_boundaries() -> str:
        """Rules that prevent Makefile and Justfile responsibility drift."""
        return """# Makefile and Justfile Boundaries

| File | Owns | May call | Must not own |
|---|---|---|---|
| `Makefile` | Build and packaging | `helpers/mk`, shell helpers, Python helpers | `Justfile`, interactive task workflows |
| `Justfile` | Task management and local workflows | `helpers/just`, shell helpers, Python helpers, Make build targets | Duplicated build implementation |
| `helpers/mk/*` | Reusable Make build fragments | shell/Python helpers | Just recipes |
| `helpers/just/*` | Reusable task recipes | shell/Python helpers, Make targets | Build logic duplicated from Make |

Required dependency direction:

```text
Justfile -> helpers/just -> helpers/shell or helpers/python
Justfile -> Makefile -> helpers/mk -> helpers/shell or helpers/python
```

Forbidden dependency direction:

```text
Makefile -X-> Justfile
```

When a command is needed by both build and task workflows, put the implementation in `helpers/shell` or `helpers/python`, then call it from the thin orchestration layer that owns the workflow.
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
        "session",
        "mcp",
    )

    spec_resource_docs = {
        "spec://agents": "agents",
        "spec://session": "session",
        "spec://context/product": "product",
        "spec://context/architecture": "architecture",
        "spec://context/stack": "stack",
        "spec://context/conventions": "conventions",
        "spec://context/commands": "commands",
        "spec://context/decisions": "decisions",
        "spec://context/roadmap": "roadmap",
        "spec://context/traceability": "traceability",
        "spec://spec-native/pipelines/ci": "ci",
        "spec://spec-native/pipelines/cd": "cd",
        "spec://pipelines/ci": "ci",
        "spec://pipelines/cd": "cd",
        "spec://schema": "schema",
    }

    def _spec_resource_reader(document: str) -> str:
        try:
            return json.dumps(_run_tool("specnative context", action="read", document=document), indent=2)
        except Exception as exc:
            return _json_error(exc)

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

    for uri, document in spec_resource_docs.items():
        def _make_resource(doc: str):
            def _resource() -> str:
                return _spec_resource_reader(doc)

            _resource.__name__ = f"resource_{doc.replace('-', '_')}"
            _resource.__doc__ = f"Read SpecNative resource {doc}."
            return _resource

        server.resource(uri)(_make_resource(document))

    @server.resource("forge://specnative/status")
    def resource_specnative_status() -> str:
        """All SpecNative specs with their states and task counts for the current repo."""
        try:
            return json.dumps(_run_tool("specnative status", action="status"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://specnative/session")
    def resource_specnative_session() -> str:
        """Current SpecNative SESSION.md handoff state for multi-agent continuity."""
        try:
            return json.dumps(_run_tool("specnative session", action="resume"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://specnative/health")
    def resource_specnative_health() -> str:
        """SpecNative project health check with missing, empty, or stale documents."""
        try:
            return json.dumps(_run_tool("specnative project", action="health-check"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://specnative/suggest-next")
    def resource_specnative_suggest_next() -> str:
        """Top recommended next actions from SpecNative project state."""
        try:
            return json.dumps(_run_tool("specnative project", action="suggest-next"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://specnative/templates")
    def resource_specnative_templates() -> str:
        """Available SpecNative spec templates and decision snippets."""
        try:
            return json.dumps(_run_tool("specnative templates", action="list-templates"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://specnative/archetypes")
    def resource_specnative_archetypes() -> str:
        """Available SpecNative built-in and local archetypes."""
        try:
            return json.dumps(_run_tool("specnative templates", action="list-archetypes"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://specnative/board")
    def resource_specnative_board() -> str:
        """SpecNative delivery board in markdown format."""
        try:
            return json.dumps(_run_tool("specnative board", format="markdown"), indent=2)
        except Exception as exc:
            return _json_error(exc)


def _register_linux_resources(server: FastMCP) -> None:
    @server.resource("forge://linux/system")
    def resource_linux_system() -> str:
        """Current Linux host identity, CPU, memory, and uptime snapshot."""
        try:
            return json.dumps(_run_tool("linux system", action="info"), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://linux/storage")
    def resource_linux_storage() -> str:
        """Current filesystem usage and inode snapshot for the working host."""
        try:
            return json.dumps(_run_tool("linux storage", action="usage", path="."), indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://linux/network")
    def resource_linux_network() -> str:
        """Current Linux interfaces, routes, and DNS context."""
        try:
            return json.dumps({
                "interfaces": _run_tool("linux network", action="interfaces"),
                "routes": _run_tool("linux network", action="routes"),
                "dns": _run_tool("linux network", action="dns"),
            }, indent=2)
        except Exception as exc:
            return _json_error(exc)

    @server.resource("forge://linux/operations-guide")
    def resource_linux_operations_guide() -> str:
        """Guide to safe Linux services, logs, storage, and network operations."""
        return """# Linux Operations Guide

- Use `linux_system` for host identity, CPU, memory, uptime, and limits.
- Use `linux_storage` for filesystem usage, inodes, mounts, and largest paths.
- Use `linux_logs` with bounded `lines`; prefer `journal` or `dmesg` over unbounded shell output.
- Use `linux_services` to inspect systemd and preview service mutations before confirmation.
- Use `linux_network` for interfaces, routes, DNS, and sockets; use `process_ports` for process ownership.
- Mutating service actions require `execute=true` and `confirm=true`.
- Do not use `shell_run` when a typed Linux tool provides the required operation.
"""

    @server.resource("forge://linux/privilege")
    def resource_linux_privilege() -> str:
        """Guide to Linux command privilege preflight and non-interactive sudo."""
        return """# Linux Privilege Preflight

Before attempting a command that may require elevated privileges, call `linux_privilege` with the exact executable and arguments.

The tool does not execute the requested command. It reports:

- whether the executable exists;
- whether the process is already root;
- whether `sudo` is installed;
- whether `sudo -n` can authenticate without a prompt;
- whether the command is allowed by the current sudoers policy;
- a recommendation such as `direct`, `sudo-non-interactive`, or `blocked`.

Do not pass shell pipelines, redirections, or compound commands. Inspect each executable separately.
"""

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
