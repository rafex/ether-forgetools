# MCP Capabilities

Documento generado por `scripts/gen_mcp_metadata.py`.

| MCP | Categorias | Tools | Resources | Prompts | Capabilities |
|---|---|---:|---:|---:|---|
| `forge-mcp-ai` | `ai` | 1 | 2 | 1 | `mcps/ai/capabilities.json` |
| `forge-mcp-build` | `go`, `npm`, `cargo`, `make` | 10 | 6 | 3 | `mcps/build/capabilities.json` |
| `forge-mcp-cloud` | `cloud` | 1 | 2 | 1 | `mcps/cloud/capabilities.json` |
| `forge-mcp-containers` | `docker`, `k8s`, `helm` | 14 | 5 | 2 | `mcps/containers/capabilities.json` |
| `forge-mcp-data` | `db` | 3 | 2 | 1 | `mcps/data/capabilities.json` |
| `forge-mcp-deps` | `deps`, `java`, `npm` | 13 | 2 | 2 | `mcps/deps/capabilities.json` |
| `forge-mcp-docs` | `docs`, `openapi`, `web` | 3 | 2 | 1 | `mcps/docs/capabilities.json` |
| `forge-mcp-file` | `fs`, `search`, `edit`, `diff`, `text`, `template`, `json`, `config` | 24 | 3 | 2 | `mcps/file/capabilities.json` |
| `forge-mcp-frontend` | `frontend`, `npm` | 5 | 2 | 2 | `mcps/frontend/capabilities.json` |
| `forge-mcp-git` | `git`, `gh` | 40 | 12 | 17 | `mcps/git/capabilities.json` |
| `forge-mcp-java` | `java` | 8 | 6 | 5 | `mcps/java/capabilities.json` |
| `forge-mcp-linux` | `process`, `diag`, `net`, `shell`, `linux` | 18 | 10 | 3 | `mcps/linux/capabilities.json` |
| `forge-mcp-observability` | `observability` | 2 | 2 | 2 | `mcps/observability/capabilities.json` |
| `forge-mcp-office` | `office` | 10 | 4 | 3 | `mcps/office/capabilities.json` |
| `forge-mcp-podman` | `podman` | 12 | 8 | 2 | `mcps/podman/capabilities.json` |
| `forge-mcp-python` | `python` | 4 | 3 | 2 | `mcps/python/capabilities.json` |
| `forge-mcp-quality` | `lint`, `test`, `security`, `secrets` | 11 | 3 | 3 | `mcps/quality/capabilities.json` |
| `forge-mcp-release` | `release`, `gh`, `docs` | 20 | 2 | 1 | `mcps/release/capabilities.json` |
| `forge-mcp-specnative` | `specnative`, `context`, `ether` | 14 | 27 | 20 | `mcps/specnative/capabilities.json` |
| `forge-mcp-websearch` | `websearch`, `web` | 3 | 2 | 0 | `mcps/websearch/capabilities.json` |

## Detalle por Dominio

### `forge-mcp-ai`

- Server: `forgetools-ai`
- Categorias: `ai`
- Tools: 1
- Resources: 2
- Prompts: 1

Tools:

- `ai_ollama`: Inspect or run Ollama models

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.

Prompts:

- `performance_analysis`: Analyse performance: process top + ports + resource usage + profiling guide.

### `forge-mcp-build`

- Server: `forgetools-build`
- Categorias: `go`, `npm`, `cargo`, `make`
- Tools: 10
- Resources: 6
- Prompts: 3

Tools:

- `cargo_build`: forgetools.cargo.build — Run cargo build and parse JSON output
- `cargo_check`: forgetools.cargo.check — Run cargo check and parse JSON output
- `cargo_test`: forgetools.cargo.test — Run cargo test and parse output
- `go_build`: forgetools.go.build — Run go build
- `go_mod`: forgetools.go.mod — Run go mod commands
- `go_test`: forgetools.go.test — Run go test with JSON output parsing
- `make_run`: forgetools.make.run — Run make targets or list available targets
- `npm_audit`: forgetools.npm.audit — Run npm audit and parse JSON output
- `npm_install`: forgetools.npm.install — Run npm install
- `npm_run`: forgetools.npm.run — Run an npm script

Resources:

- `forge://build/standards/java`: Java construction standards for Maven, Gradle, and Ant.
- `forge://build/standards/make-just-boundaries`: Rules that prevent Makefile and Justfile responsibility drift.
- `forge://build/standards/python`: Python construction standards using uv, pip, and wheel.
- `forge://build/standards/structure`: Repository build and task-management structure standards.
- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.

Prompts:

- `build_project_scaffold`: Plan a responsibility-separated Makefile/Justfile and helpers layout.
- `dependency_upgrade`: Safely upgrade dependencies: audit → upgrade → test → verify.
- `go_project_analysis`: Comprehensive analysis of a Go project: build, test, lint, mod, and security.

### `forge-mcp-cloud`

- Server: `forgetools-cloud`
- Categorias: `cloud`
- Tools: 1
- Resources: 2
- Prompts: 1

Tools:

- `cloud_whoami`: Show active identity for AWS, GCP, or Azure

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.

Prompts:

- `repo_health_check`: Full health dashboard for a repository.

### `forge-mcp-containers`

- Server: `forgetools-containers`
- Categorias: `docker`, `k8s`, `helm`
- Tools: 14
- Resources: 5
- Prompts: 2

Tools:

- `docker_build`: forgetools.docker.build — Build a Docker image
- `docker_compose`: forgetools.docker.compose — Docker Compose operations
- `docker_exec`: forgetools.docker.exec — Execute a command in a Docker container
- `docker_inspect`: forgetools.docker.inspect — Inspect a Docker container
- `docker_logs`: forgetools.docker.logs — Fetch Docker container logs
- `docker_ps`: forgetools.docker.ps — List Docker containers
- `helm_diff`: Compare Helm release changes before install or upgrade
- `helm_install`: forgetools.helm.install — Install a Helm chart
- `helm_status`: forgetools.helm.status — Helm release status
- `helm_upgrade`: forgetools.helm.upgrade — Upgrade (or install) a Helm release
- `k8s_contexts`: forgetools.k8s.contexts — List and switch kubectl contexts
- `k8s_logs`: forgetools.k8s.logs — Fetch Kubernetes pod logs with filters
- `k8s_pods`: forgetools.k8s.pods — List Kubernetes pods with status
- `k8s_rollout`: forgetools.k8s.rollout — Manage Kubernetes rollouts

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
- `forge://docker/containers`: Running Docker containers snapshot.
- `forge://k8s/pods`: Current Kubernetes pod status across all namespaces.
- `forge://policy/podman-ports-bastion`: Mandatory Podman port allocation policy for the bastion host.

Prompts:

- `docker_debug`: Debug a failing Docker container: logs → inspect → exec → fix.
- `k8s_deploy`: Deploy an app to Kubernetes: deploy → rollout → verify → health check.

### `forge-mcp-data`

- Server: `forgetools-data`
- Categorias: `db`
- Tools: 3
- Resources: 2
- Prompts: 1

Tools:

- `db_migrations`: forgetools.db.migrations — Check database migration status
- `db_query`: forgetools.db.query — Run a SQL query against sqlite, postgres, or mysql
- `db_schema`: forgetools.db.schema — Inspect database schema

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.

Prompts:

- `database_migration`: Plan, create, test, and prepare rollback for a database migration.

### `forge-mcp-deps`

- Server: `forgetools-deps`
- Categorias: `deps`, `java`, `npm`
- Tools: 13
- Resources: 2
- Prompts: 2

Tools:

- `deps_npm`: Fetch npm package metadata
- `deps_pypi`: Fetch PyPI package metadata
- `java_format`: Format Java source files with google-java-format when available
- `java_gradle`: forgetools.java.gradle — Run Gradle tasks with structured output
- `java_jdt`: Inspect Java projects using JDT-style source and symbol analysis helpers
- `java_maven`: forgetools.java.maven — Run Maven goals with structured output
- `java_maven_central`: Query Maven Central for artifact versions, metadata, and checksums
- `java_maven_modules`: Inspect Maven multi-module project structure and module metadata
- `java_stacktrace`: forgetools.java.parse_stacktrace — Parse Java stack traces into structured data
- `java_test_report`: forgetools.java.test_report — Parse JUnit/Surefire XML test reports
- `npm_audit`: forgetools.npm.audit — Run npm audit and parse JSON output
- `npm_install`: forgetools.npm.install — Run npm install
- `npm_run`: forgetools.npm.run — Run an npm script

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.

Prompts:

- `dependency_upgrade`: Safely upgrade dependencies: audit → upgrade → test → verify.
- `maven_dependency_research`: Research Maven Central for a dependency: find, compare, get checksums, and add to POM.

### `forge-mcp-docs`

- Server: `forgetools-docs`
- Categorias: `docs`, `openapi`, `web`
- Tools: 3
- Resources: 2
- Prompts: 1

Tools:

- `docs_changelog`: forgetools.docs.changelog — Generate changelog from git commits
- `openapi_parse`: forgetools.openapi.parse — Parse OpenAPI 2/3 YAML or JSON spec files
- `web_fetch`: Fetch a webpage and extract clean readable text using XPath.

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.

Prompts:

- `api_design`: Spec-first API design: OpenAPI spec → stub → implement → test.

### `forge-mcp-file`

- Server: `forgetools-file`
- Categorias: `fs`, `search`, `edit`, `diff`, `text`, `template`, `json`, `config`
- Tools: 24
- Resources: 3
- Prompts: 2

Tools:

- `config_gitignore`: Add common .gitignore patterns for macOS and/or Claude Code.
- `config_validate`: Validate config files: JSON, YAML, TOML, XML, Properties, .env, INI
- `diff_dirs`: Compare two directory trees. Returns added, removed, and modified file lists.
- `diff_json`: Semantic diff of two JSON documents.
- `diff_yaml`: Semantic diff of two YAML documents.
- `edit_bulk_rename`: forgetools.edit.bulk_rename — Rename files matching a pattern
- `edit_insert`: forgetools.edit.insert — Insert lines into a file at a specific position
- `edit_replace_lines`: forgetools.edit.replace_lines — Replace a range of lines in a file
- `fs_checksum`: forgetools.fs.checksum — Compute file checksums using stdlib hashlib
- `fs_diff`: forgetools.fs.diff — Diff two files or git refs
- `fs_disk_usage`: Measure directory usage with ncdu JSON export or a portable Python fallback
- `fs_find_by_type`: Find files by semantic type such as code, docs, config, images, or archives
- `fs_head`: Read the first lines of a file or matching files with structured metadata
- `fs_operations`: Inspect, create, copy, move, delete, archive, or extract filesystem paths safely
- `fs_read`: Read a text file with metadata; accepts file, filePath, or path as the file location
- `fs_tail`: Read the last lines of a file or matching files with structured metadata
- `fs_tree`: forgetools.fs.tree — Directory tree with smart filters
- `json_query`: Query JSON documents using dotted paths and array indexes
- `search_find_files`: forgetools.search.find_files — Find files by name/extension
- `search_grep`: Search source files with structured match/context events and backend metadata.
- `search_replace`: forgetools.search.search_replace — Bulk find and replace in files
- `search_todo`: Find TODO markers without traversing dependency, cache, or worktree trees.
- `template_scaffold`: Generate files from a named template and variable map
- `text_audit_chars`: Audit and optionally fix invisible/problematic characters in text files

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
- `forge://config/gitignore`: Current .gitignore content and missing preset analysis.

Prompts:

- `gitignore_setup`: Audit and patch .gitignore for macOS metadata and Claude Code files.
- `new_tool_scaffold`: Scaffold a new forgetools module following the ForgeResult pattern.

### `forge-mcp-frontend`

- Server: `forgetools-frontend`
- Categorias: `frontend`, `npm`
- Tools: 5
- Resources: 2
- Prompts: 2

Tools:

- `frontend_assets`: Check referenced local assets in HTML/Markdown files
- `frontend_detect`: Detect common frontend stacks
- `npm_audit`: forgetools.npm.audit — Run npm audit and parse JSON output
- `npm_install`: forgetools.npm.install — Run npm install
- `npm_run`: forgetools.npm.run — Run an npm script

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.

Prompts:

- `bug_investigation`: Structured bug hunt: logs + git blame + stacktrace + grep.
- `performance_analysis`: Analyse performance: process top + ports + resource usage + profiling guide.

### `forge-mcp-git`

- Server: `forgetools-git`
- Categorias: `git`, `gh`
- Tools: 40
- Resources: 12
- Prompts: 17

Tools:

- `gh_actions`: forgetools.gh.actions — GitHub Actions workflow status
- `gh_actions_logs`: Fetch and summarize logs for GitHub Actions workflow runs or jobs
- `gh_actions_trigger`: Trigger a GitHub Actions workflow dispatch with structured inputs
- `gh_actions_validate`: Validate GitHub Actions workflow files and CI configuration
- `gh_api_releases`: Query GitHub release metadata through the GitHub API
- `gh_api_repo`: Query GitHub repository metadata through the GitHub API
- `gh_api_search`: Search GitHub repositories, issues, pull requests, or code through the GitHub API
- `gh_branch`: Inspect, create, delete, or protect GitHub branches with structured output
- `gh_issue_create`: Create a GitHub issue with title, body, labels, and assignees
- `gh_issue_list`: forgetools.gh.issue_list — List GitHub issues
- `gh_issue_view`: View a GitHub issue with comments, labels, assignees, and state
- `gh_pr_create`: forgetools.gh.pr_create — Create a GitHub pull request
- `gh_pr_diff`: Fetch and summarize the diff for a GitHub pull request
- `gh_pr_list`: forgetools.gh.pr_list — List GitHub pull requests
- `gh_pr_merge`: Merge a GitHub pull request using the selected merge strategy
- `gh_pr_review`: forgetools.gh.pr_review — View PR review comments and status
- `gh_release`: forgetools.gh.release — Create a GitHub release
- `gh_repo_status`: Aggregate repository PRs, checks, reviewers, issues, and branch state
- `git_backport_plan`: Plan safe cherry-pick backports to release branches
- `git_blame`: forgetools.git.blame — Git blame with structured output
- `git_branch`: forgetools.git.branch — List and manage git branches
- `git_cherry_pick`: pick commits onto the current branch
- `git_commit`: Create structured git commits with validation and optional dry-run planning
- `git_commit_plan`: Build an explicit multi-commit plan from changed files
- `git_conflicts`: forgetools.git.conflicts — List conflicted files
- `git_diff`: forgetools.git.diff — Git diff with structured output
- `git_log`: forgetools.git.log — Git commit history
- `git_multi_repo`: Inspect and coordinate git status across multiple repositories
- `git_operations`: Preview or execute Git synchronization, recovery, branch, remote administration, bisect, and maintenance operations safely
- `git_pr_workflow`: forgetools.git.pr_workflow — Create a GitHub PR via branch + push + gh pr create
- `git_preflight`: Validate branch, remote, and protection status before push or merge
- `git_stack_plan`: Plan stacked PR branches from ordered task names
- `git_stash`: forgetools.git.stash — List and manage git stashes
- `git_status`: forgetools.git.status — Git repository status
- `git_submodule_status`: forgetools.git.submodule_status — Git submodule status
- `git_submodule_sync`: forgetools.git.submodule_sync — Sync and update git submodules
- `git_tag`: forgetools.git.tag — List, create, or delete git tags
- `git_worktree`: Manage git worktrees: list, add, remove, move, prune, lock/unlock, status
- `git_worktree_merge_plan`: Plan integration and merge readiness for worktree sessions
- `git_worktree_workflow`: Manage parallel git worktree workflows from plan through integration

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
- `forge://gh/ci-status`: Latest GitHub Actions workflow runs for the current repository.
- `forge://gh/open-prs`: Open pull requests for the current repository.
- `forge://gh/repo-status`: Aggregated GitHub repository status: PRs, checks, reviewers, issues, and branches.
- `forge://git/branches`: All branches with ahead/behind tracking information for the cwd repository.
- `forge://git/log`: Last 20 commits of the cwd repository.
- `forge://git/parallel-workflow`: Status of active parallel worktree workflow sessions in the cwd repo.
- `forge://git/pr-workflows`: Reference guide for stacked PR and backport planning tools.
- `forge://git/status`: Current git working-tree status of the cwd repository.
- `forge://git/worktree-guide`: Reference guide for git worktree concepts and the parallel workflow engine.
- `forge://git/worktrees`: Active git worktrees for the cwd repository.

Prompts:

- `best_practice_commits`: Analiza todos los cambios del repo, propone el plan de commits siguiendo
- `code_review`: Review a pull request: diff, context, checks, and review comments.
- `commit_amend`: Amend the last commit: fix the message and/or add forgotten staged files.
- `commit_history_cleanup`: Clean up commit history before opening a PR: squash WIP commits, fix messages.
- `conventional_commit`: Craft and apply a Conventional Commit following the CC spec (conventionalcommits.org).
- `debug_ci_failure`: Diagnose and fix a failing GitHub Actions workflow run.
- `git_backport_workflow`: Plan and execute a safe backport workflow.
- `git_multi_commit_workflow`: Split current changes into an explicit multi-commit plan.
- `git_stacked_pr_workflow`: Plan and execute a stacked PR workflow safely.
- `git_worktree_parallel_merge_workflow`: Manage, integrate, and merge multiple worktree tasks safely.
- `multi_repo_health`: Health check for multiple side-by-side git repositories.
- `parallel_worktree_workflow`: AI-agent guide for parallel git worktree development and integration.
- `pr_create_flow`: Complete flow to create a well-structured GitHub Pull Request.
- `pr_stack`: Manage a stack of dependent Pull Requests (stacked PRs / PR chains).
- `release_workflow`: Prepare and publish a new release.
- `worktree_feature`: Isolate a single feature in its own git worktree (simpler than parallel workflow).
- `worktree_hotfix`: Emergency hotfix in an isolated worktree — minimal blast radius, fast turnaround.

### `forge-mcp-java`

- Server: `forgetools-java`
- Categorias: `java`
- Tools: 8
- Resources: 6
- Prompts: 5

Tools:

- `java_format`: Format Java source files with google-java-format when available
- `java_gradle`: forgetools.java.gradle — Run Gradle tasks with structured output
- `java_jdt`: Inspect Java projects using JDT-style source and symbol analysis helpers
- `java_maven`: forgetools.java.maven — Run Maven goals with structured output
- `java_maven_central`: Query Maven Central for artifact versions, metadata, and checksums
- `java_maven_modules`: Inspect Maven multi-module project structure and module metadata
- `java_stacktrace`: forgetools.java.parse_stacktrace — Parse Java stack traces into structured data
- `java_test_report`: forgetools.java.test_report — Parse JUnit/Surefire XML test reports

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
- `forge://java/standards/dependency-policy`: Java dependency and version upgrade policy.
- `forge://java/standards/project-structure`: Java project layout and module structure standards.
- `forge://java/standards/testing-strategy`: Java testing strategy, levels, and quality gates.
- `forge://test/coverage`: Latest test coverage summary for the cwd project.

Prompts:

- `java_code_review_strict`: Run a strict Java code review workflow for a target scope.
- `java_new_service_scaffold`: Scaffold a new Java service following local standards.
- `java_project_analysis`: Comprehensive analysis of a Java/Maven project.
- `maven_dependency_research`: Research Maven Central for a dependency: find, compare, get checksums, and add to POM.
- `security_audit`: Run a comprehensive security audit on the codebase.

### `forge-mcp-linux`

- Server: `forgetools-linux`
- Categorias: `process`, `diag`, `net`, `shell`, `linux`
- Tools: 18
- Resources: 10
- Prompts: 3

Tools:

- `diag_env`: forgetools.diag.env_validate — Validate required environment variables
- `diag_health`: forgetools.diag.health — Check availability of required tools
- `diag_port`: forgetools.diag.port_check — Check if a port is in use
- `linux_logs`: Read Linux journal, kernel, and file logs with bounded output
- `linux_network`: Inspect Linux interfaces, routes, DNS, and socket connections
- `linux_privilege`: Check command availability and non-interactive sudo authorization without executing it
- `linux_services`: Inspect or safely operate systemd services
- `linux_storage`: Inspect Linux filesystem usage, mounts, inodes, and largest paths
- `linux_system`: Inspect Linux host identity, CPU, memory, uptime, and resource limits
- `net_health`: forgetools.net.health_check — Check if a service endpoint is healthy
- `net_http`: Execute HTTP requests with structured status, headers, body, and timing data
- `process_inspect`: Inspect a process by PID with command, resource usage, and open-file details
- `process_kill`: forgetools.process.kill — Kill a process by PID or name
- `process_port`: forgetools.process.port — Check what process is using a port
- `process_ports`: List listening or connected network ports with owning process information
- `process_ps`: forgetools.process.ps — List running processes
- `process_top`: Show top local processes by CPU or memory usage
- `shell_run`: forgetools.shell.run — Execute arbitrary shell commands

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
- `forge://diag/env`: Environment variables relevant to development tools.
- `forge://diag/health`: System health: availability of required development tools.
- `forge://linux/network`: Current Linux interfaces, routes, and DNS context.
- `forge://linux/operations-guide`: Guide to safe Linux services, logs, storage, and network operations.
- `forge://linux/privilege`: Guide to Linux command privilege preflight and non-interactive sudo.
- `forge://linux/storage`: Current filesystem usage and inode snapshot for the working host.
- `forge://linux/system`: Current Linux host identity, CPU, memory, and uptime snapshot.
- `forge://process/listening`: Snapshot of all listening ports on the local machine.

Prompts:

- `bug_investigation`: Structured bug hunt: logs + git blame + stacktrace + grep.
- `linux_host_audit`: Audit a Linux host across system, storage, network, logs, and services.
- `performance_analysis`: Analyse performance: process top + ports + resource usage + profiling guide.

### `forge-mcp-observability`

- Server: `forgetools-observability`
- Categorias: `observability`
- Tools: 2
- Resources: 2
- Prompts: 2

Tools:

- `observability_log_parse`: Parse JSON lines logs and summarize levels
- `observability_log_tail`: Tail logs with optional filtering

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.

Prompts:

- `bug_investigation`: Structured bug hunt: logs + git blame + stacktrace + grep.
- `performance_analysis`: Analyse performance: process top + ports + resource usage + profiling guide.

### `forge-mcp-office`

- Server: `forgetools-office`
- Categorias: `office`
- Tools: 10
- Resources: 4
- Prompts: 3

Tools:

- `office_docx_create`: Create a DOCX from Markdown, HTML, or plain text
- `office_markdown_html`: Convert Markdown to a standalone HTML document
- `office_pdf_append_tables`: Append CSV/XLSX table pages to a PDF
- `office_pdf_create`: Create a PDF from Markdown, HTML, or plain text
- `office_pdf_images`: Extract embedded PDF page images when available
- `office_pdf_merge`: Merge PDFs using pypdf, pdfunite, or qpdf
- `office_pdf_metadata`: Extract PDF metadata, page count, and document flags
- `office_pdf_stamp`: Stamp text on each page of a PDF
- `office_pdf_text`: Extract text from a PDF using pdftotext or pypdf
- `office_table_report`: Convert CSV/XLSX tables into Markdown, HTML, PDF, or DOCX reports

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
- `forge://office/dependency-policy`: Office MCP dependency policy and optional local tool expectations.
- `forge://office/report-workflow`: Recommended workflow for generating business reports with mcp-office.

Prompts:

- `api_design`: Spec-first API design: OpenAPI spec → stub → implement → test.
- `office_appendix_bundle`: Create a PDF report bundle with tabular appendices.
- `office_executive_report`: Plan and generate an executive report with PDF/DOCX outputs.

### `forge-mcp-podman`

- Server: `forgetools-podman`
- Categorias: `podman`
- Tools: 12
- Resources: 8
- Prompts: 2

Tools:

- `podman_build`: Build an image from a Containerfile with qualified base images on a local or remote Podman service
- `podman_connection`: Preview or execute Podman system connection operations for local and SSH remote services
- `podman_image_reference`: Validate a deterministic fully-qualified Podman registry image reference
- `podman_images`: List images stored by a local or remote Podman service
- `podman_inspect`: Inspect a Podman container, image, pod, volume, or network
- `podman_logs`: Read Podman container logs
- `podman_ports`: Inspect occupied Podman published ports
- `podman_ps`: List Podman containers
- `podman_pull`: Pull a fully-qualified Docker Hub or GHCR image into a local or remote Podman store
- `podman_run`: Preview or execute a Podman container start with bastion-safe published ports
- `podman_select_port`: Select the first free port in the approved bastion range
- `podman_validate_ports`: Validate Podman port publications against bastion policy

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
- `forge://podman/containerfiles`: Containerfile/Dockerfile standards plus bounded files discovered in the current repository.
- `forge://podman/containerignore`: .containerignore/.dockerignore standards plus bounded files discovered in the current repository.
- `forge://podman/image-references`: Deterministic image reference rules for Docker Hub and GitHub Container Registry.
- `forge://podman/policy/bastion-ports`: Bastion Podman port allocation policy.
- `forge://podman/ports`: Occupied and available Podman published ports grouped by policy range.
- `forge://podman/remote`: Remote rootless Podman connection workflow over SSH or a Podman service URL.

Prompts:

- `docker_debug`: Debug a failing Docker container: logs → inspect → exec → fix.
- `podman_remote_workflow`: Plan a safe remote rootless Podman deployment through a named connection.

### `forge-mcp-python`

- Server: `forgetools-python`
- Categorias: `python`
- Tools: 4
- Resources: 3
- Prompts: 2

Tools:

- `python_mypy`: Run mypy type checks
- `python_pytest`: Run pytest and return structured output
- `python_ruff`: Run ruff check/format
- `python_uv`: Run uv commands for Python projects

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
- `forge://python/standards/uv`: Local Python/uv workflow standards.

Prompts:

- `dependency_upgrade`: Safely upgrade dependencies: audit → upgrade → test → verify.
- `new_tool_scaffold`: Scaffold a new forgetools module following the ForgeResult pattern.

### `forge-mcp-quality`

- Server: `forgetools-quality`
- Categorias: `lint`, `test`, `security`, `secrets`
- Tools: 11
- Resources: 3
- Prompts: 3

Tools:

- `lint_checkstyle`: forgetools.lint.checkstyle — Parse Checkstyle XML result files
- `lint_eslint`: forgetools.lint.eslint — Run ESLint and parse JSON output
- `lint_golangci`: lint and parse JSON output
- `lint_pylint`: forgetools.lint.pylint — Run Pylint and parse JSON output
- `secrets_scan`: forgetools.secrets.scan — Scan for secrets in files
- `security_eslint`: Run ESLint-oriented security checks and return structured findings
- `security_owasp`: Run OWASP dependency checks and parse security findings
- `security_spotbugs`: Run SpotBugs security analysis and parse structured findings
- `test_coverage`: forgetools.test.coverage — Parse Cobertura coverage.xml reports
- `test_coverage_report`: Parse coverage reports and return summary metrics and uncovered files
- `test_junit_report`: forgetools.test.junit_report — Parse JUnit XML test reports

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
- `forge://quality/gates`: Recommended quality gates before commit or release.

Prompts:

- `code_review`: Review a pull request: diff, context, checks, and review comments.
- `repo_health_check`: Full health dashboard for a repository.
- `security_audit`: Run a comprehensive security audit on the codebase.

### `forge-mcp-release`

- Server: `forgetools-release`
- Categorias: `release`, `gh`, `docs`
- Tools: 20
- Resources: 2
- Prompts: 1

Tools:

- `docs_changelog`: forgetools.docs.changelog — Generate changelog from git commits
- `gh_actions`: forgetools.gh.actions — GitHub Actions workflow status
- `gh_actions_logs`: Fetch and summarize logs for GitHub Actions workflow runs or jobs
- `gh_actions_trigger`: Trigger a GitHub Actions workflow dispatch with structured inputs
- `gh_actions_validate`: Validate GitHub Actions workflow files and CI configuration
- `gh_api_releases`: Query GitHub release metadata through the GitHub API
- `gh_api_repo`: Query GitHub repository metadata through the GitHub API
- `gh_api_search`: Search GitHub repositories, issues, pull requests, or code through the GitHub API
- `gh_branch`: Inspect, create, delete, or protect GitHub branches with structured output
- `gh_issue_create`: Create a GitHub issue with title, body, labels, and assignees
- `gh_issue_list`: forgetools.gh.issue_list — List GitHub issues
- `gh_issue_view`: View a GitHub issue with comments, labels, assignees, and state
- `gh_pr_create`: forgetools.gh.pr_create — Create a GitHub pull request
- `gh_pr_diff`: Fetch and summarize the diff for a GitHub pull request
- `gh_pr_list`: forgetools.gh.pr_list — List GitHub pull requests
- `gh_pr_merge`: Merge a GitHub pull request using the selected merge strategy
- `gh_pr_review`: forgetools.gh.pr_review — View PR review comments and status
- `gh_release`: forgetools.gh.release — Create a GitHub release
- `gh_repo_status`: Aggregate repository PRs, checks, reviewers, issues, and branch state
- `release_precheck`: Run basic pre-release checks

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.

Prompts:

- `release_workflow`: Prepare and publish a new release.

### `forge-mcp-specnative`

- Server: `forgetools-specnative`
- Categorias: `specnative`, `context`, `ether`
- Tools: 14
- Resources: 27
- Prompts: 20

Tools:

- `context_diff_summary`: forgetools.context.diff_summary — Summarize git diff between two refs
- `context_repo_size`: Measure repository size, language distribution, and git metadata for context planning
- `context_summarize`: block project summary for code agents
- `ether_catalog`: List Ether ecosystem repositories and their local/remote availability
- `specnative_artifacts`: List or read SpecNative persistent context artifacts such as decisions, architecture records, and conventions
- `specnative_backlog`: Capture SpecNative backlog items as task previews or backlog notes without changing delivery boards
- `specnative_board`: Build a SpecNative delivery board from task files in json, markdown, or mermaid format
- `specnative_context`: Read, write, or list SpecNative context documents for the current repository
- `specnative_initiative`: Create or update SpecNative initiatives from repository context
- `specnative_project`: Health-check, suggest, snapshot, and safely refine SpecNative project documents
- `specnative_session`: Resume, checkpoint, update tasks, or clear SpecNative multi-agent session state
- `specnative_status`: Report SpecNative specs, initiatives, states, and task progress
- `specnative_templates`: List or apply SpecNative archetypes, spec templates, and decision snippets
- `specnative_upstream`: Fetch current SpecNative documentation/releases or preview and execute the official installer

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
- `forge://context/repo`: Repository size, language breakdown, and git metadata for cwd.
- `forge://context/summary`: AI-readable codebase summary: structure, languages, and key patterns.
- `forge://specnative/archetypes`: Available SpecNative built-in and local archetypes.
- `forge://specnative/board`: SpecNative delivery board in markdown format.
- `forge://specnative/health`: SpecNative project health check with missing, empty, or stale documents.
- `forge://specnative/session`: Current SpecNative SESSION.md handoff state for multi-agent continuity.
- `forge://specnative/status`: All SpecNative specs with their states and task counts for the current repo.
- `forge://specnative/suggest-next`: Top recommended next actions from SpecNative project state.
- `forge://specnative/templates`: Available SpecNative spec templates and decision snippets.
- `forge://specnative/upstream/releases`: List stable and prerelease versions published by SpecNative upstream.
- `spec://agents`: Read SpecNative resource agents.
- `spec://context/architecture`: Read SpecNative resource architecture.
- `spec://context/commands`: Read SpecNative resource commands.
- `spec://context/conventions`: Read SpecNative resource conventions.
- `spec://context/decisions`: Read SpecNative resource decisions.
- `spec://context/product`: Read SpecNative resource product.
- `spec://context/roadmap`: Read SpecNative resource roadmap.
- `spec://context/stack`: Read SpecNative resource stack.
- `spec://context/traceability`: Read SpecNative resource traceability.
- `spec://pipelines/cd`: Read SpecNative resource cd.
- `spec://pipelines/ci`: Read SpecNative resource ci.
- `spec://schema`: Read SpecNative resource schema.
- `spec://session`: Read SpecNative resource session.
- `spec://spec-native/pipelines/cd`: Read SpecNative resource cd.
- `spec://spec-native/pipelines/ci`: Read SpecNative resource ci.

Prompts:

- `capture_backlog`: Classify and capture a requested backlog item without creating parallel state.
- `close_initiative`: Official SpecNative v0.8 prompt to close an initiative.
- `handoff`: Official SpecNative v0.8 alias for multi-agent handoff.
- `implement_task`: Official SpecNative v0.8 prompt to implement a single task.
- `init_project_guided`: Official SpecNative v0.8 alias for guided project initialization.
- `plan_tasks`: Official SpecNative v0.8 prompt to derive tasks from a spec.
- `record_architecture`: Record a durable architecture artifact after applying the placement test.
- `record_convention`: Record a durable coding or process convention after applying the placement test.
- `record_decision`: Record a persistent SpecNative decision after applying the placement test.
- `repo_health_check`: Full health dashboard for a repository.
- `review_against_spec`: Review implementation state against a SpecNative spec before closing.
- `specnative`: Universal SpecNative entry point that routes one user request.
- `specnative_close_initiative`: Close a SpecNative initiative and update traceability.
- `specnative_handoff`: Generate a SpecNative multi-agent handoff.
- `specnative_implement_task`: Implement a specific SpecNative task.
- `specnative_init_project`: Initialize SpecNative project context with guided document updates.
- `specnative_plan_tasks`: Derive tasks from an existing SpecNative spec.
- `specnative_workflow`: Full SpecNative spec-first development workflow guide.
- `start_feature`: Start a new feature using git worktree isolation + SpecNative spec scaffold.
- `start_initiative`: Official SpecNative v0.8 prompt to start an initiative.

### `forge-mcp-websearch`

- Server: `forgetools-websearch`
- Categorias: `websearch`, `web`
- Tools: 3
- Resources: 2
- Prompts: 0

Tools:

- `web_fetch`: Fetch a webpage and extract clean readable text using XPath.
- `websearch_ddg_search`: Search DuckDuckGo using DDGS and return normalized JSON results.
- `websearch_visit`: Visit a URL and return parsed text/metadata for browsing workflows.

Resources:

- `forge://capabilities`: Machine-readable capabilities manifest for this domain server.
- `forge://catalog`: List tools available in this domain server.
