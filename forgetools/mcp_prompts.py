"""Prompt definitions shared by domain MCP servers."""
from __future__ import annotations

def start_feature(initiative: str, problem: str) -> str:
    """Start a new feature using git worktree isolation + SpecNative spec scaffold.

    Follows the official SpecNative 9-step agent workflow sequence.

    Args:
        initiative: Short hyphenated name for the feature (e.g. 'user-auth')
        problem:    One-sentence description of the problem being solved
    """
    return f'# Start Feature: `{initiative}`\n\n**Problem:** {problem}\n\nSigue el flujo oficial SpecNative de 9 pasos. **No omitas pasos.**\n\n---\n\n## Paso 1 — Navegación (entry point)\n```\n# Lee el README.md del folder actual primero\nfs_read(path="README.md")\n```\n\n## Paso 2 — Coherencia de iniciativa\n```\nspecnative_context(action="read", document="roadmap")\n```\nVerifica que `{initiative}` sea coherente con las prioridades actuales.\n\n## Paso 3 — Contexto mínimo\n```\nspecnative_context(action="read", document="product")\nspecnative_context(action="read", document="architecture")\n```\nCarga SOLO lo necesario. No leas todo el repositorio.\n\n## Paso 4 — Respetar decisiones previas\n```\nspecnative_context(action="decisions")\n```\nLee los DEC-XXXX antes de escribir una sola línea de spec.\n\n## Paso 5 — Crear workspace aislado + spec\n```\ngit_worktree(action="add", path="../.claude/worktrees/{initiative}",\n             branch="ai/{initiative}", new_branch=True)\n\n# Preview primero:\nspecnative_initiative(action="start", initiative="{initiative}",\n                      problem="{problem}", owner="<owner>")\n# Si el preview es correcto, escribir:\nspecnative_initiative(action="start", initiative="{initiative}",\n                      problem="{problem}", owner="<owner>", write=True)\n```\n\n**Estados de spec válidos:** `draft` → `active` → `blocked` | `done` | `superseded`\n\n## Paso 6 — Derivar tareas\n```\nspecnative_context(action="read", document="conventions")\nspecnative_context(action="read", document="stack")\n\n# Preview:\nspecnative_initiative(action="plan", initiative="{initiative}")\n# Escribir:\nspecnative_initiative(action="plan", initiative="{initiative}", write=True)\n```\n\n**Estados de tarea válidos:** `todo` → `in_progress` → `blocked` | `done`\n\n## Paso 7 — Implementar (workflows/IMPLEMENTATION.md)\n```\nspecnative_initiative(action="implement", initiative="{initiative}")\n# Devuelve: target_tasks, spec_summary, conventions, agent_sequence,\n#           placement_test para decidir dónde documentar cada cosa\n```\n\nActualiza cada tarea antes de comenzar y al terminar:\n```\nspecnative_initiative(action="state", initiative="{initiative}",\n                      task_id="TASK-...", state="in_progress", write=True)\n# ... código ...\nspecnative_initiative(action="state", initiative="{initiative}",\n                      task_id="TASK-...", state="done", write=True)\n```\n\n## Paso 8 — Registrar decisiones persistentes\nSolo si el tradeoff SOBREVIVE a esta iniciativa:\n```\nspecnative_initiative(\n    action="decision",\n    title="<título de la decisión>",\n    context="<por qué fue necesaria esta decisión>",\n    decision="<qué se decidió>",\n    consequences="<trade-offs e impactos>",\n    decision_state="proposed",   # luego: accepted | deprecated | replaced\n    write=True\n)\n```\n**Usa el placement_test** (devuelto por implement) para decidir si va en\nDECISIONS.md o en otro documento.\n\n## Paso 9 — Cerrar y actualizar trazabilidad\n```\nspecnative_initiative(action="review", initiative="{initiative}")\n# Cuando ready_to_close = true:\nspecnative_initiative(action="close", initiative="{initiative}", write=True)\n# TRACEABILITY.md se actualiza automáticamente en close\n```\n'

def code_review(pr_number: int, depth: str='standard') -> str:
    """Review a pull request: diff, context, checks, and review comments.

    Args:
        pr_number: GitHub PR number to review
        depth:     'quick' (diff only) | 'standard' (diff + checks) | 'deep' (full analysis)
    """
    steps = f'# Code Review: PR #{pr_number}\n\n## 1. Get PR overview\n```\ngh_pr_review(number={pr_number})\n```\n\n## 2. See files changed\n```\ngh_pr_diff(action="files", number={pr_number})\n```\n\n## 3. Read the diff\n```\ngh_pr_diff(action="diff", number={pr_number})\n```\n'
    if depth in ('standard', 'deep'):
        steps += f'\n## 4. Check CI status\n```\ngh_pr_merge(action="check", number={pr_number})\n```\n\n## 5. Read project conventions\n```\nspecnative_context(action="read", document="conventions")\n```\n'
    if depth == 'deep':
        steps += f'\n## 6. Summarize context of changed files\n```\ncontext_diff_summary()\n```\n\n## 7. Check for secrets in diff\n```\nsecrets_scan()\n```\n\n## 8. Run linting on changed files\n```\nlint_eslint()   # for JS/TS\nlint_pylint()   # for Python\nlint_checkstyle()  # for Java\n```\n\n## 9. Review decisions for conflicts\n```\nspecnative_context(action="decisions")\n```\n'
    steps += f'\n## Final step: Add review comment or merge\n```\n# To request changes:\ngh_issue_view(action="comments", number={pr_number})\n\n# To merge when approved:\ngh_pr_merge(action="merge", number={pr_number}, method="squash")\n```\n'
    return steps

def security_audit(target_dir: str='.', scope: str='full') -> str:
    """Run a comprehensive security audit on the codebase.

    Args:
        target_dir: Directory to audit (default: current directory)
        scope:      'deps' (dependencies only) | 'code' (static analysis) | 'full' (both)
    """
    steps = f'# Security Audit: `{target_dir}`\n\n'
    if scope in ('deps', 'full'):
        steps += '## 1. Scan dependencies for CVEs (OWASP)\n```\nsecurity_owasp(action="scan", cwd="{target_dir}")\n# Parse results:\nsecurity_owasp(action="report", cwd="{target_dir}")\n```\n\n## 2. Audit npm dependencies\n```\nnpm_audit(cwd="{target_dir}")\n```\n'.format(target_dir=target_dir)
    if scope in ('code', 'full'):
        steps += '## 3. Java static analysis (SpotBugs + Find Security Bugs)\n```\nsecurity_spotbugs(action="scan", cwd="{target_dir}", security_only=True)\n```\n\n## 4. JavaScript/TypeScript static analysis (ESLint security)\n```\nsecurity_eslint(action="scan", cwd="{target_dir}")\n```\n\n## 5. Scan for secrets and credentials in code\n```\nsecrets_scan(cwd="{target_dir}")\n```\n\n## 6. Validate GitHub Actions workflows\n```\ngh_actions_validate(cwd="{target_dir}")\n```\n'.format(target_dir=target_dir)
    steps += '## Summary\nAfter running the above, check:\n- `ok: false` results indicate findings requiring action\n- CRITICAL/HIGH CVEs block releases\n- Security bug prefixes: SQL_INJECTION, XSS_, PATH_TRAVERSAL, HARD_CODE_PASSWORD\n- Built-in rules: no-eval, no-new-func, no-implied-eval\n'
    return steps

def release_workflow(version: str, repo: str='', branch: str='main') -> str:
    """Prepare and publish a new release.

    Args:
        version: Semantic version string, e.g. 'v2.1.0'
        repo:    GitHub 'owner/repo' (leave empty to use current repo)
        branch:  Branch to release from (default: main)
    """
    repo_flag = f", repo='{repo}'" if repo else ''
    return f'# Release Workflow: `{version}`\n\n## 1. Verify repo is clean\n```\ngit_status()\ngit_multi_repo(action="status")\n```\n\n## 2. Check all tests pass\n```\njava_maven(goal="verify")       # Java projects\ngo_test()                       # Go projects\nnpm_run(script="test")          # JS/TS projects\n```\n\n## 3. Run security scan\n```\nsecurity_owasp(action="scan")\nsecrets_scan()\n```\n\n## 4. Generate / update changelog\n```\ndocs_changelog(action="generate", version="{version}", output="CHANGELOG.md")\n```\n\n## 5. Create release tag\n```\ngit_tag(action="create", name="{version}", message="Release {version}")\n```\n\n## 6. Create GitHub release with auto-generated notes\n```\ngh_release(tag="{version}", title="Release {version}"{repo_flag})\n```\n\n## 7. Verify release assets\n```\ngh_api_releases(action="get", slug="<owner>/<repo>", tag="{version}")\n```\n\n## 8. Update traceability (SpecNative projects)\n```\nspecnative_initiative(action="close", initiative="release-{version}", write=True)\n```\n'

def debug_ci_failure(run_id: int) -> str:
    """Diagnose and fix a failing GitHub Actions workflow run.

    Args:
        run_id: The workflow run ID from GitHub Actions
    """
    return f'# Debug CI Failure: Run #{run_id}\n\n## 1. Get job overview\n```\ngh_actions_logs(action="jobs", run_id={run_id})\n```\n\n## 2. Read failed steps only\n```\ngh_actions_logs(action="failed", run_id={run_id})\n```\n\n## 3. Tail the full log (last 200 lines)\n```\ngh_actions_logs(action="tail", run_id={run_id}, lines=200)\n```\n\n## 4. Validate the workflow YAML\n```\ngh_actions_validate()\n```\n\n## 5. Check environment and tool availability\n```\ndiag_health()\ndiag_env()\n```\n\n## 6. Look for related issues\n```\ngh_api_search(action="issues", query="CI failure run {run_id}", repo="<owner>/<repo>")\n```\n\n## 7. Re-run failed jobs only (after fix)\n```\ngh_actions_trigger(action="rerun", run_id={run_id}, failed_only=True)\n```\n\n## 8. Watch the re-run\n```\ngh_actions_trigger(action="watch", run_id={run_id}, timeout=300)\n```\n'

def java_project_analysis(project_dir: str='.') -> str:
    """Comprehensive analysis of a Java/Maven project.

    Args:
        project_dir: Root directory of the Java project (default: cwd)
    """
    return f'# Java Project Analysis: `{project_dir}`\n\n## 1. Discover Maven module structure\n```\njava_maven_modules(action="summary", dir="{project_dir}", pattern="*")\njava_maven_modules(action="list",    dir="{project_dir}")\n```\n\n## 2. Locate Java Language Server (eclipse.jdt.ls)\n```\njava_jdt(action="locate")\n```\n\n## 3. Check code formatting\n```\njava_format(action="check", path="{project_dir}")\n```\n\n## 4. Run build\n```\njava_maven(goal="compile -DskipTests", cwd="{project_dir}")\n```\n\n## 5. Run tests and collect coverage\n```\njava_maven(goal="verify", cwd="{project_dir}")\ntest_coverage_report(action="report", cwd="{project_dir}")\ntest_coverage_report(action="check",  cwd="{project_dir}", min=80)\n```\n\n## 6. Static security analysis\n```\nsecurity_spotbugs(action="scan", cwd="{project_dir}", security_only=True)\nsecurity_owasp(action="scan",    cwd="{project_dir}")\n```\n\n## 7. Lint (Checkstyle)\n```\nlint_checkstyle(cwd="{project_dir}")\n```\n\n## 8. Parse any stacktraces in logs\n```\njava_stacktrace(cwd="{project_dir}")\n```\n'

def repo_health_check(repo_dir: str='.') -> str:
    """Full health dashboard for a repository.

    Args:
        repo_dir: Repository root directory (default: cwd)
    """
    return f'# Repository Health Check: `{repo_dir}`\n\n## 1. Size and language breakdown\n```\ncontext_repo_size(cwd="{repo_dir}")\n```\n\n## 2. Git state\n```\ngit_status(cwd="{repo_dir}")\ngit_worktree(action="list", cwd="{repo_dir}")\n```\n\n## 3. Recent activity\n```\ngit_log(limit=10, cwd="{repo_dir}")\ncontext_diff_summary(cwd="{repo_dir}")\n```\n\n## 4. Open PRs and issues\n```\ngh_pr_list(state="open")\ngh_issue_list(state="open")\n```\n\n## 5. CI status (last 5 runs)\n```\ngh_actions(limit=5, cwd="{repo_dir}")\n```\n\n## 6. Security\n```\nsecrets_scan(cwd="{repo_dir}")\ngh_actions_validate(cwd="{repo_dir}")\n```\n\n## 7. Code quality\n```\nlint_eslint(cwd="{repo_dir}")    # JS/TS\nlint_pylint(cwd="{repo_dir}")    # Python\nlint_checkstyle(cwd="{repo_dir}") # Java\n```\n\n## 8. Test coverage\n```\ntest_coverage_report(action="find", cwd="{repo_dir}")\ntest_coverage_report(action="summary", cwd="{repo_dir}")\n```\n\n## 9. Dependencies\n```\nnpm_audit(cwd="{repo_dir}")\nsecurity_owasp(action="find", cwd="{repo_dir}")\n```\n\n## 10. SpecNative compliance (if applicable)\n```\nspecnative_status(action="validate", repo="{repo_dir}")\nspecnative_status(action="status",   repo="{repo_dir}")\n```\n'

def specnative_workflow(initiative: str, action: str='status') -> str:
    """Full SpecNative spec-first development workflow guide.

    Args:
        initiative: Initiative name (e.g. 'user-auth', 'payment-api')
        action:     'status' | 'start' | 'implement' | 'review' | 'close'
    """
    _SPEC_STATES = 'draft → active → blocked | done | superseded'
    _TASK_STATES = 'todo → in_progress → blocked | done'
    _DEC_STATES = 'proposed → accepted | deprecated | replaced'
    _PLACEMENT_BRIEF = '¿Desaparece al terminar la iniciativa? → SPEC.md\n¿Debe respetarse en la próxima iniciativa? → DECISIONS.md\n¿Explica el producto? → PRODUCT.md  |  ¿Guía prioridad temporal? → ROADMAP.md\n¿Describe estructura del sistema? → ARCHITECTURE.md'
    if action == 'status':
        return f'# SpecNative Status: `{initiative}`\n\n## Estados válidos\n- Spec:     `{_SPEC_STATES}`\n- Tarea:    `{_TASK_STATES}`\n- Decisión: `{_DEC_STATES}`\n\n## 1. Salud del repositorio (valida los 17 archivos requeridos)\n```\nspecnative_status(action="validate")\nspecnative_status(action="status")\nspecnative_status(action="list-specs")\n```\n\n## 2. Leer spec e estado de tareas\n```\nspecnative_context(action="read-spec", initiative="{initiative}")\nspecnative_context(action="list-tasks", initiative="{initiative}")\n```\n\n## 3. Decisiones relevantes (tradeoffs persistentes)\n```\nspecnative_context(action="decisions")\n```\n\n## Placement test (¿dónde va este contenido?)\n```\n{_PLACEMENT_BRIEF}\n```\n'
    if action == 'start':
        return f'# SpecNative Start: `{initiative}`\n\nSigue la secuencia oficial de 9 pasos.\n\n## 1. Navegación y coherencia\n```\nfs_read(path="README.md")\nspecnative_context(action="read", document="roadmap")\n```\n\n## 2. Contexto mínimo + decisiones previas\n```\nspecnative_context(action="read", document="product")\nspecnative_context(action="read", document="architecture")\nspecnative_context(action="decisions")\n```\n\n## 3. Crear spec (estado inicial: `draft`)\n```\n# Preview:\nspecnative_initiative(action="start", initiative="{initiative}",\n                      problem="<describe the problem>", owner="<owner>")\n# Escribir:\nspecnative_initiative(action="start", initiative="{initiative}",\n                      problem="<describe the problem>", owner="<owner>", write=True)\n```\n\n## 4. Derivar tareas (estado inicial de cada tarea: `todo`)\n```\nspecnative_context(action="read", document="conventions")\n# Preview:\nspecnative_initiative(action="plan", initiative="{initiative}")\n# Escribir:\nspecnative_initiative(action="plan", initiative="{initiative}", write=True)\n```\n\n## 5. Activar spec al comenzar implementación\n```\nspecnative_initiative(action="state", initiative="{initiative}",\n                      state="active", write=True)\n```\n'
    if action == 'implement':
        return f'# SpecNative Implement: `{initiative}`\n\n## 1. Cargar contexto de implementación (9-step sequence incluida)\n```\nspecnative_initiative(action="implement", initiative="{initiative}")\n```\nEl resultado incluye:\n- `target_tasks` — tareas en estado `todo` o `in_progress`\n- `spec_summary`, `conventions`, `architecture`, `stack`\n- `agent_sequence` — los 9 pasos oficiales\n- `placement_test` — árbol de decisiones sobre dónde documentar\n\n## 2. Por cada tarea, ciclo: todo → in_progress → done\n```\n# Al comenzar:\nspecnative_initiative(action="state", initiative="{initiative}",\n                      task_id="TASK-...", state="in_progress", write=True)\n\n# Buscar código relacionado:\nsearch_grep(pattern="<clase o función relevante>")\nfs_find_by_type(extensions=".java,.py,.ts")\n\n# Al terminar:\nspecnative_initiative(action="state", initiative="{initiative}",\n                      task_id="TASK-...", state="done", write=True)\n```\n\n## 3. Si una tarea se bloquea\n```\nspecnative_initiative(action="state", initiative="{initiative}",\n                      task_id="TASK-...", state="blocked", write=True)\n# Documentar el bloqueo en el SPEC.md con --state blocked\nspecnative_initiative(action="state", initiative="{initiative}",\n                      state="blocked", write=True)\n```\n\n## 4. Registrar decisiones persistentes (usar placement_test)\n```\n# Solo si el tradeoff SOBREVIVE a esta iniciativa:\nspecnative_initiative(\n    action="decision",\n    title="<título>",\n    context="<por qué>",\n    decision="<qué se decidió>",\n    consequences="<impactos>",\n    decision_state="proposed",\n    write=True\n)\n```\n**Placement test rápido:**\n```\n{_PLACEMENT_BRIEF}\n```\n'
    if action == 'review':
        return f'# SpecNative Review: `{initiative}`\n\n## 1. Verificar que todas las tareas estén en `done`\n```\nspecnative_initiative(action="review", initiative="{initiative}")\n# ready_to_close debe ser true para continuar\n```\n\n## 2. Verificar tests\n```\njava_maven(goal="verify")\ngo_test()\nnpm_run(script="test")\n```\n\n## 3. Seguridad y calidad\n```\nsecrets_scan()\nsecurity_spotbugs(action="scan", security_only=True)\nlint_checkstyle()\nlint_eslint()\nlint_pylint()\n```\n\n## 4. Confirmar estado del spec\nEl spec debe estar en `active`. Si todo está bien, pasar a `close`.\n'
    if action == 'close':
        return f'# SpecNative Close: `{initiative}`\n\n## 1. Revisión final\n```\nspecnative_initiative(action="review", initiative="{initiative}")\n# ready_to_close debe ser true\n```\n\n## 2. Registrar decisiones finales que sobrevivan (si aplica)\n```\n# Usa el placement_test para confirmar que va en DECISIONS.md:\n# "¿Debe respetarse en la próxima iniciativa?" → sí → DECISIONS.md\nspecnative_initiative(\n    action="decision",\n    title="<título>",\n    context="<por qué>",\n    decision="<qué se decidió>",\n    consequences="<impactos>",\n    decision_state="proposed",\n    write=True\n)\n```\n\n## 3. Cerrar el spec (estado → `done`, actualiza TRACEABILITY.md)\n\n```\nspecnative_initiative(action="close", initiative="{initiative}")\n# Preview looks good? Write it:\nspecnative_initiative(action="close", initiative="{initiative}", write=True)\n```\n\n## 4. Commit and create PR\n```\ngit_commit(action="commit")\ngh_pr_create(title="feat({initiative}): ...", body="Closes spec SPEC-...")\n```\n'
    return f"Unknown action '{action}'. Use: status | start | implement | review | close"

def specnative_init_project(
    name: str,
    problem: str,
    users: str,
    goals: str,
    stack: str = "",
) -> str:
    """Initialize SpecNative project context with guided document updates.

    Args:
        name:    Project name
        problem: Product/problem statement
        users:   Target users
        goals:   Observable goals
        stack:   Known technology stack
    """
    return f'# SpecNative Init Project: `{name}`\n\n## 1. Check gaps\n```\nspecnative_project(action="health-check")\nspecnative_project(action="suggest-next")\n```\n\n## 2. Fill PRODUCT.md\n```\nspecnative_project(\n  action="refine-document", document="product", write=True,\n  what_changed="Initial guided SpecNative setup",\n  content="""# PRODUCT.md\n\n## Problema\n{problem}\n\n## Usuarios\n{users}\n\n## Objetivos\n{goals}\n\n## No objetivos\n\n## Valor diferencial\n"""\n)\n```\n\n## 3. Fill STACK.md if known\n```\nspecnative_project(action="update-section", document="stack", section="Lenguajes y runtimes", content="{stack}", write=True)\n```\n\n## 4. Continue interviewing\nUse `specnative_project(action="read-template", document="<doc>")` before writing architecture, conventions and commands.\n'

def specnative_handoff(summary: str, next_steps: str, decisions_made: str = "") -> str:
    """Generate a SpecNative multi-agent handoff.

    Args:
        summary:        What was accomplished
        next_steps:     Ordered next actions
        decisions_made: Optional decisions not yet recorded
    """
    return f'# SpecNative Handoff\n\n## Summary\n{summary}\n\n## Next steps\n{next_steps}\n\n## Actions\n```\nspecnative_session(\n  action="checkpoint",\n  initiative="<current-initiative>",\n  task_id="<current-task>",\n  intent="{summary}",\n  next_steps="""{next_steps}""",\n  context_notes="""{decisions_made or "none"}""",\n  write=True,\n)\n```\n\nIf persistent decisions were made:\n```\nspecnative_initiative(action="decision", title="<title>", context="<context>", decision="<decision>", consequences="<consequences>", write=True)\n```\n\nThe next agent should begin with:\n```\nspecnative_session(action="resume")\n```\n'

def specnative_plan_tasks(initiative: str) -> str:
    """Derive tasks from an existing SpecNative spec.

    Args:
        initiative: Initiative name
    """
    return f'# SpecNative Plan Tasks: `{initiative}`\n\n## Steps\n```\nspecnative_context(action="read-spec", initiative="{initiative}")\nspecnative_context(action="read", document="planning")\nspecnative_context(action="read", document="architecture")\nspecnative_context(action="read", document="decisions")\n```\n\nCreate task preview:\n```\nspecnative_initiative(action="plan", initiative="{initiative}")\n```\n\nIf the plan is correct:\n```\nspecnative_initiative(action="plan", initiative="{initiative}", write=True)\n```\n'

def specnative_implement_task(initiative: str, task_id: str) -> str:
    """Implement a specific SpecNative task.

    Args:
        initiative: Initiative name
        task_id: Task ID
    """
    return f'# SpecNative Implement Task: `{initiative}` / `{task_id}`\n\n## Steps\n```\nspecnative_session(action="resume")\nspecnative_initiative(action="implement", initiative="{initiative}", task_id="{task_id}")\nspecnative_initiative(action="state", initiative="{initiative}", task_id="{task_id}", state="in_progress", write=True)\n```\n\nAfter implementation and validation:\n```\nspecnative_initiative(action="state", initiative="{initiative}", task_id="{task_id}", state="done", write=True)\nspecnative_session(action="checkpoint", initiative="{initiative}", task_id="{task_id}", intent="Completed task", next_steps="Review and continue", write=True)\n```\n'

def specnative_close_initiative(initiative: str) -> str:
    """Close a SpecNative initiative and update traceability.

    Args:
        initiative: Initiative name
    """
    return f'# SpecNative Close Initiative: `{initiative}`\n\n## Verify\n```\nspecnative_initiative(action="review", initiative="{initiative}")\nspecnative_context(action="read", document="traceability")\n```\n\n## Close\n```\nspecnative_initiative(action="close", initiative="{initiative}")\n# If preview is correct:\nspecnative_initiative(action="close", initiative="{initiative}", write=True)\nspecnative_session(action="clear", write=True)\n```\n'

def multi_repo_health(base_dir: str, pattern: str='*') -> str:
    """Health check for multiple side-by-side git repositories.

    Args:
        base_dir: Parent directory containing the repos
        pattern:  Glob filter for repo names (e.g. 'ether-*')
    """
    return f'# Multi-Repo Health Check\n\nBase directory: `{base_dir}`\nPattern: `{pattern}`\n\n## 1. Fast status (no network)\n```\ngit_multi_repo(action="status", dir="{base_dir}", pattern="{pattern}", no_fetch=True)\n```\n\n## 2. Full sync check (with fetch — slower)\n```\ngit_multi_repo(action="check", dir="{base_dir}", pattern="{pattern}")\n```\n\n## 3. Summary dashboard\n```\ngit_multi_repo(action="summary", dir="{base_dir}", pattern="{pattern}")\n```\nThe summary shows:\n- `dirty`: repos with uncommitted changes\n- `out_of_sync`: repos behind/ahead of origin\n- `missing_license`: repos without license headers in source files\n\n## 4. Discover Maven modules across all repos\n```\njava_maven_modules(action="summary", dir="{base_dir}", pattern="{pattern}")\n```\n\n## 5. Fix dirty repos\nFor each repo in `dirty` list:\n```\ngit_status(cwd="{base_dir}/<repo-name>")\ngit_diff(cwd="{base_dir}/<repo-name>")\n```\n'

def new_tool_scaffold(tool_name: str, category: str, description: str) -> str:
    """Scaffold a new forgetools module following the ForgeResult pattern.

    Args:
        tool_name:   Short name for the tool (e.g. 'format', 'analyze')
        category:    Category prefix (e.g. 'java', 'git', 'fs')
        description: One-line description of what the tool does
    """
    full_key = f'{category} {tool_name}'
    module = f"forgetools.{category}.{tool_name.replace('-', '_')}"
    mcp_name = full_key.replace(' ', '_').replace('-', '_')
    return f'''# New Tool: `{full_key}`\n\nModule path: `{module}`\nMCP name: `{mcp_name}`\nDescription: {description}\n\n## 1. Generate scaffold\n```\n# Use the meta-tool to generate the boilerplate:\nshell_run(cmd="python3 scripts/new_tool.py --category {category} --name {tool_name} --description '{description}'")\n```\n\n## 2. Implement `run()` in `forgetools/{category}/{tool_name.replace('-', '_')}.py`\n\nThe file must follow this pattern:\n```python\nfrom forgetools._result import ForgeResult, Timer\nfrom forgetools._runner import run_command\n\nTOOL = "{category}.{tool_name.replace('-', '_')}"\n\ndef run(*, action: str = "...", cwd: str | None = None) -> ForgeResult:\n    with Timer() as t:\n        # ... implementation ...\n        return ForgeResult.success(TOOL, {{...}}, t.elapsed_ms)\n```\n\n## 3. Register in `forgetools/_forge_cli.py`\nAdd to REGISTRY:\n```python\n"{full_key}": "{module}",\n```\n\n## 4. Verify\n```\nconfig_validate(file="forgetools/_forge_cli.py")\nshell_run(cmd="python3 -c \\"import {module}; print('OK')\\"")\n```\n\n## 5. Reload MCP\nAfter `git pull`:\nToggle forgetools off → on in `/mcp` to pick up the new tool `{mcp_name}`.\n'''

def maven_dependency_research(query: str, project_dir: str='.') -> str:
    """Research Maven Central for a dependency: find, compare, get checksums, and add to POM.

    Args:
        query:       What you're looking for (e.g. 'json serialization', 'jwt library')
        project_dir: Project directory where pom.xml lives (default: cwd)
    """
    return f'''# Maven Dependency Research: `{query}`\n\nYou are researching Maven Central to find the best library for: **{query}**\n\n## Phase 1 — Discover candidates\n```\njava_maven_central(action="search", query="{query}", rows=10)\n```\nFrom the results, pick the top 2-3 candidates with the most `version_count`\nand recent `timestamp`. Note their `group_id` and `artifact_id`.\n\n## Phase 2 — Evaluate each candidate\nFor each candidate `groupId:artifactId`:\n```\n# Full details: description, URL, SCM, latest version\njava_maven_central(action="info", coords="<groupId>:<artifactId>")\n\n# Version history (check for active maintenance)\njava_maven_central(action="versions", coords="<groupId>:<artifactId>", rows=10)\n\n# Get dependency snippets for the latest version\njava_maven_central(action="dependency", coords="<groupId>:<artifactId>")\n```\n\n## Phase 3 — Verify integrity before adding\nOnce you have chosen the library:\n```\n# Get all checksums for the chosen version\njava_maven_central(action="checksums", coords="<groupId>:<artifactId>:<version>")\n\n# Optionally review the POM for transitive dependencies\njava_maven_central(action="pom", coords="<groupId>:<artifactId>:<version>")\n```\n\n## Phase 4 — Check project context\n```\n# Find the project POM\njava_maven_modules(action="list", dir="{project_dir}")\n\n# Check if the dependency is already present\nsearch_grep(pattern="<artifactId>.*</artifactId>", paths="{project_dir}/pom.xml")\n```\n\n## Phase 5 — Add to project\nThe `dependency` action returns ready-to-paste snippets:\n- `maven_xml`       → paste inside `<dependencies>` in pom.xml\n- `gradle`          → paste in `build.gradle`\n- `gradle_kotlin`   → paste in `build.gradle.kts`\n\nAfter adding:\n```\njava_maven(goal="dependency:resolve", cwd="{project_dir}")\n```\n\n## Decision checklist\n- Latest version released in last 12 months? (check `timestamp`)\n- More than 10 versions? (indicates stability)\n- SCM URL points to active repo? (check `scm_url`)\n- No known CVEs? (run `security_owasp` after adding)\n- SHA1 matches what the project's security policy requires?\n'''

def parallel_worktree_workflow(session: str, tasks: str, base_branch: str='main', merge_method: str='merge') -> str:
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
    task_list = [t.strip() for t in tasks.split(',') if t.strip()]
    int_branch = f'ai/{session}-integration'
    task_items = '\n'.join((f'  - `ai/{session}-{t}` → `../.claude/worktrees/{session}-{t}`' for t in task_list))
    task_status_calls = '\n'.join((f'git_worktree_workflow(action="integrate", session="{session}", task="{t}", merge_method="{merge_method}")' for t in task_list))
    return f'''# Parallel Worktree Workflow: `{session}`\n\n**Tasks:** {', '.join(task_list)}\n**Base branch:** `{base_branch}`\n**Integration branch:** `{int_branch}`\n**Merge method:** `{merge_method}`\n\nYou are an AI agent operating in parallel across {len(task_list)} isolated git worktrees.\nFollow **every step in order**. Do not skip steps.\n\n---\n\n## Phase 1 — Plan (no writes)\n\nRead the current repo state and preview the topology.\n\n```\n# 1a. Read the worktree guide\n# Resource: forge://git/worktree-guide\n\n# 1b. Verify repo health\ngit_status()\ngit_worktree(action="list")\n\n# 1c. Preview the session — check for conflicts before creating anything\ngit_worktree_workflow(\n    action="plan",\n    session="{session}",\n    tasks={json.dumps(task_list)},\n    base_branch="{base_branch}",\n    merge_method="{merge_method}",\n)\n```\n\n**If `conflicts` list is non-empty** in the plan output:\n- A worktree path or branch already exists\n- Resolve before continuing (rename, remove, or abort that session)\n\n---\n\n## Phase 2 — Init (creates branches + worktrees)\n\n```\ngit_worktree_workflow(\n    action="init",\n    session="{session}",\n    tasks={json.dumps(task_list)},\n    base_branch="{base_branch}",\n)\n```\n\nThis creates:\n{task_items}\n\n**Expected output**: `created` list with {len(task_list)} worktrees + 1 integration branch.\nIf any errors appear, read them — most are path conflicts or branch-already-exists.\n\n---\n\n## Phase 3 — Parallel implementation\n\nWork independently in each task worktree. **Each task is a separate directory.**\nNever commit to `{base_branch}` or `{int_branch}` directly.\n\nFor each task `<task>` in [{', '.join((f'"{t}"' for t in task_list))}]:\n\n```\n# Check the worktree is clean before starting\ngit_worktree_workflow(action="status", session="{session}")\n\n# Work in the task's directory:\n#   ../.claude/worktrees/{session}-<task>/\n\n# After finishing the task — commit in that worktree:\ngit_commit(action="commit", cwd="../.claude/worktrees/{session}-<task>")\n```\n\n**Rules while working:**\n- One worktree = one concern (e.g., `models` only touches the data layer)\n- Avoid modifying the same file in two worktrees (causes merge conflicts)\n- Commit early and often within the worktree; squash later via `merge_method`\n\n---\n\n## Phase 4 — Sync (if base_branch advanced)\n\nIf other changes landed on `{base_branch}` while you were working:\n\n```\ngit_worktree_workflow(\n    action="sync",\n    session="{session}",\n    base_branch="{base_branch}",\n    merge_method="{merge_method}",\n)\n```\n\nResolve any conflicts reported in `errors`, then re-run sync.\n\n---\n\n## Phase 5 — Integrate (one task at a time)\n\nAfter **each** task is committed and clean, integrate it:\n\n```\n{task_status_calls}\n```\n\nAfter each call, check `errors`. A non-empty `errors` means a merge conflict:\n```\n# In the integration worktree or main repo, resolve conflicts:\ngit_status(cwd="../.claude/worktrees/{session}-integration")   # if it exists\n# or:\ngit_status()   # if integration branch was checked out in the main repo\n```\n\nMonitor overall progress:\n```\ngit_worktree_workflow(action="status", session="{session}")\n```\n\n`ready_to_integrate` — tasks with commits not yet in integration\n`in_progress` — tasks still dirty (uncommitted changes)\n\n---\n\n## Phase 6 — Finalize\n\nWhen **all** tasks are integrated (`ready_to_integrate` is empty):\n\n```\ngit_worktree_workflow(\n    action="finalize",\n    session="{session}",\n    target_branch="{base_branch}",\n    merge_method="{merge_method}",\n    cleanup=True,\n)\n```\n\nThis:\n1. Merges `{int_branch}` → `{base_branch}` using `{merge_method}`\n2. Removes all task worktrees (`cleanup=True`)\n3. Deletes task branches and the integration branch\n\n**After finalize:**\n```\ngit_status()           # verify {base_branch} is clean\ngit_log(limit=5)       # verify the merge commit appears\n\n# Push to remote:\nshell_run(cmd="git push origin {base_branch}")\n\n# Optional: create a PR instead of pushing directly\ngh_pr_create(\n    title="feat({session}): parallel implementation of {tasks}",\n    body="Parallel worktree session `{session}` integrating: {tasks}",\n    base="{base_branch}",\n)\n```\n\n---\n\n## Emergency abort\n\nIf something went wrong and you need to clean up:\n\n```\ngit_worktree_workflow(action="abort", session="{session}")\n```\n\nThis removes all worktrees and deletes all session branches.\nThe main repo is returned to the state before `init`.\n\n---\n\n## Quick reference\n\n| Action | When to call |\n|--------|-------------|\n| `plan` | Before init — sanity check, preview names |\n| `init` | Once — creates all worktrees |\n| `status` | Anytime — see dirty/ahead-behind |\n| `sync` | When `{base_branch}` has new commits |\n| `integrate` | After each task is committed |\n| `finalize` | When all tasks integrated |\n| `abort` | Emergency rollback |\n'''

def bug_investigation(symptom: str, component: str='') -> str:
    """Structured bug hunt: logs + git blame + stacktrace + grep.

    Args:
        symptom:   Short description of the observed bug (e.g. 'NullPointerException in checkout')
        component: Optional component/module name to focus the search (e.g. 'payment-service')
    """
    scope = f' in `{component}`' if component else ''
    path_hint = component if component else '.'
    return f'# Bug Investigation: `{symptom}`{scope}\n\nYou are systematically hunting the root cause of a bug.\nWork through each phase **in order**, stopping early if you find the culprit.\n\n## Phase 1 — Reproduce and observe\n```\n# Check current repo state\ngit_status()\ngit_log(limit=10)\n\n# Find recent changes related to the component\ncontext_diff_summary()\n```\n\n## Phase 2 — Search for the symptom in code and logs\n```\n# Grep for error message / keyword\nsearch_grep(pattern="{symptom[:60]}", paths="{path_hint}")\n\n# Search for TODOs or known issues\nsearch_todo(paths="{path_hint}")\n```\n\n## Phase 3 — Parse any stacktraces\n```\n# If it is a Java service:\njava_stacktrace(cwd="{path_hint}")\n\n# Tail recent application logs\nfs_tail(path="<log-file>", lines=100)\n```\n\n## Phase 4 — Blame and history\n```\n# Find the file most likely containing the bug, then:\ngit_blame(file="<suspect-file>")\n\n# See what changed recently in that area\ngit_log(path="<suspect-file>", limit=20)\ngit_diff(ref="HEAD~5..HEAD", path="<suspect-file>")\n```\n\n## Phase 5 — Check environment\n```\ndiag_health()\ndiag_env()\ndiag_port(port=<service-port>)\n```\n\n## Phase 6 — Run tests to confirm fix scope\n```\n# Run tests for the affected component\njava_maven(goal="test -pl {path_hint}", cwd=".")   # Java\ngo_test(pkg="./{path_hint}/...")                   # Go\nnpm_run(script="test", cwd="{path_hint}")          # JS/TS\n```\n\n## Resolution checklist\n- [ ] Root cause identified (file + line)\n- [ ] Regression test added or updated\n- [ ] Fix committed with reference to this symptom\n- [ ] Related TODOs / tech-debt items created if needed\n'

def database_migration(migration_name: str, db_type: str='postgresql') -> str:
    """Plan, create, test, and prepare rollback for a database migration.

    Args:
        migration_name: Descriptive name for the migration (e.g. 'add-user-roles-table')
        db_type:        Database engine: postgresql | mysql | sqlite (default: postgresql)
    """
    return f'''# Database Migration: `{migration_name}`\n\n**Database:** {db_type}\n\n## Phase 1 — Understand current schema\n```\n# View all current tables\ndb_schema(action="tables", database="<your-database>")\n\n# View schema for tables you plan to modify\ndb_schema(action="describe", database="<your-database>", table="<table-name>")\n\n# Check pending migrations\ndb_migrations(action="status")\n```\n\n## Phase 2 — Check migration history\n```\ndb_migrations(action="list")\ndb_migrations(action="pending")\n```\n\n## Phase 3 — Plan the migration\nBefore writing SQL, answer:\n- Which tables/columns change?\n- Are there foreign key constraints?\n- Will this lock tables? (large tables need online DDL)\n- What is the rollback path?\n\n```\n# Preview the migration file location\ndb_migrations(action="create", name="{migration_name}", preview=True)\n```\n\n## Phase 4 — Create the migration\n```\ndb_migrations(action="create", name="{migration_name}")\n# Edit the generated file to add UP and DOWN SQL\n```\n\nExample UP migration (`{db_type}`):\n```sql\n-- UP\nALTER TABLE users ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'member';\nCREATE INDEX idx_users_role ON users(role);\n\n-- DOWN (rollback)\nDROP INDEX IF EXISTS idx_users_role;\nALTER TABLE users DROP COLUMN role;\n```\n\n## Phase 5 — Validate and run\n```\n# Dry-run against a test/staging database first\ndb_migrations(action="run", dry_run=True)\n\n# Apply the migration\ndb_migrations(action="run")\n\n# Verify schema updated\ndb_schema(action="tables", database="<your-database>")\ndb_schema(action="describe", database="<your-database>", table="<affected-table>")\n```\n\n## Phase 6 — Smoke test\n```\n# Run a quick query to verify data integrity\ndb_query(query="SELECT COUNT(*) FROM <affected-table>", database="<your-database>")\n```\n\n## Phase 7 — Rollback plan (keep ready)\n```\n# If rollback needed:\ndb_migrations(action="rollback", steps=1)\ndb_schema(action="tables", database="<your-database>")\n```\n\n## Checklist\n- [ ] Schema change reviewed for locking risk\n- [ ] DOWN migration tested on a copy of production data\n- [ ] Migration idempotent (can be run twice safely)\n- [ ] Application code compatible with both old and new schema (if zero-downtime)\n'''

def docker_debug(container_name: str) -> str:
    """Debug a failing Docker container: logs → inspect → exec → fix.

    Args:
        container_name: Name or ID of the Docker container to debug
    """
    return f'''# Docker Debug: `{container_name}`\n\n## Phase 1 — Observe running containers\n```\ndocker_ps()\n```\n\n## Phase 2 — Tail container logs\n```\n# Last 100 lines\ndocker_logs(container="{container_name}", tail=100)\n\n# Follow logs for 30 seconds to catch transient errors\ndocker_logs(container="{container_name}", follow=True, timeout=30)\n```\n\n## Phase 3 — Inspect container configuration\n```\ndocker_inspect(container="{container_name}")\n```\n\nLook for:\n- `State.Status` — is it `running`, `exited`, or `restarting`?\n- `State.ExitCode` — non-zero indicates a crash\n- `State.OOMKilled` — true means the container ran out of memory\n- `HostConfig.PortBindings` — are ports exposed correctly?\n- `Mounts` — are volumes mounted at the expected paths?\n- `Config.Env` — are environment variables set correctly?\n\n## Phase 4 — Check environment and port availability\n```\ndiag_health()\nprocess_port(port=<expected-port>)\n```\n\n## Phase 5 — Exec into the container (if still running)\n```\ndocker_exec(container="{container_name}", cmd="sh -c 'env && ps aux'")\n\n# Check disk space inside container\ndocker_exec(container="{container_name}", cmd="df -h")\n\n# Check if the expected binary/process is running\ndocker_exec(container="{container_name}", cmd="ps aux")\n```\n\n## Phase 6 — Review compose configuration (if applicable)\n```\ndocker_compose(action="config")\ndocker_compose(action="ps")\n```\n\n## Phase 7 — Common fixes\n\n| Symptom | Likely cause | Fix |\n|---------|-------------|-----|\n| ExitCode 1, no logs | Missing env var | Check `Config.Env`, add to compose |\n| OOMKilled = true | Memory limit too low | Increase `mem_limit` in compose |\n| Port already in use | Host port conflict | `process_port(port=X)` to find owner |\n| Health check failing | Wrong endpoint/port | Review `Healthcheck` in inspect output |\n| Volume not found | Path typo | Check `Mounts` section |\n\n## Phase 8 — Rebuild if config changed\n```\ndocker_build(context=".", tag="{container_name}:debug")\ndocker_compose(action="up", service="{container_name}", build=True)\n```\n'''

def dependency_upgrade(ecosystem: str='', scope: str='all') -> str:
    """Safely upgrade dependencies: audit → upgrade → test → verify.

    Args:
        ecosystem: 'npm' | 'maven' | 'gradle' | 'go' | 'cargo' | '' (auto-detect)
        scope:     'security' (CVEs only) | 'minor' (patch+minor) | 'all' (major too)
    """
    eco_hint = ecosystem or 'auto-detected'
    return f'# Dependency Upgrade: `{eco_hint}` (scope: {scope})\n\n## Phase 1 — Audit current state\n```\n# JavaScript / Node.js\nnpm_audit(cwd=".")\n\n# Java (Maven / Gradle)\nsecurity_owasp(action="scan", cwd=".")\nsecurity_owasp(action="report", cwd=".")\n\n# Go modules\ngo_mod(action="tidy")\ngo_mod(action="verify")\n\n# Rust / Cargo\ncargo_check(cwd=".")\n```\n\n## Phase 2 — Identify outdated dependencies\n```\n# Node.js — list outdated packages\nshell_run(cmd="npm outdated --json")\n\n# Maven — display available updates\njava_maven(goal="versions:display-dependency-updates")\njava_maven(goal="versions:display-plugin-updates")\n\n# Go — list available upgrades\nshell_run(cmd="go list -u -m all")\n\n# Cargo\nshell_run(cmd="cargo outdated")\n```\n\n## Phase 3 — Upgrade (adjust scope as needed)\n\n### Security fixes only (`scope=security`)\n```\n# Node.js\nnpm_audit(action="fix", cwd=".")\n\n# Maven: update only CVE-affected deps manually in pom.xml\njava_maven_central(action="search", query="<vulnerable-library>")\n```\n\n### Minor + patch updates (`scope=minor`)\n```\n# Node.js\nshell_run(cmd="npm update")\nnpm_install(cwd=".")\n\n# Maven\njava_maven(goal="versions:use-latest-releases -DallowMajorUpdates=false")\njava_maven(goal="versions:commit")\n\n# Go\nshell_run(cmd="go get -u ./... && go mod tidy")\n```\n\n### All updates including major (`scope=all`)\n```\n# Review each major bump carefully — breaking changes likely!\n# Node.js\nshell_run(cmd="npx npm-check-updates -u && npm install")\n\n# Maven — manually update version properties in pom.xml\n# then:\njava_maven(goal="dependency:resolve")\n```\n\n## Phase 4 — Verify integrity\n```\n# Node.js\nnpm_audit(cwd=".")\nnpm_run(script="build", cwd=".")\n\n# Java\njava_maven(goal="verify", cwd=".")\n\n# Go\ngo_build(cwd=".")\ngo_mod(action="verify")\n\n# Rust\ncargo_build(cwd=".")\ncargo_test(cwd=".")\n```\n\n## Phase 5 — Run full test suite\n```\nnpm_run(script="test", cwd=".")         # JS/TS\njava_maven(goal="test", cwd=".")        # Java\ngo_test(cwd=".")                        # Go\ncargo_test(cwd=".")                     # Rust\n```\n\n## Phase 6 — Scan for new vulnerabilities introduced\n```\nsecrets_scan(cwd=".")\nsecurity_owasp(action="scan", cwd=".")\nnpm_audit(cwd=".")\n```\n\n## Checklist\n- [ ] All CVEs resolved (no HIGH/CRITICAL remaining)\n- [ ] All tests passing after upgrade\n- [ ] Changelog / release notes reviewed for breaking changes\n- [ ] Lock file committed (`package-lock.json`, `go.sum`, `Cargo.lock`)\n'

def k8s_deploy(app: str, image: str, namespace: str='default') -> str:
    """Deploy an app to Kubernetes: deploy → rollout → verify → health check.

    Args:
        app:       Application/deployment name (e.g. 'my-api')
        image:     Full Docker image reference (e.g. 'ghcr.io/org/my-api:v1.2.3')
        namespace: Kubernetes namespace (default: default)
    """
    return f'''# Kubernetes Deploy: `{app}`\n\n**Image:** `{image}`\n**Namespace:** `{namespace}`\n\n## Phase 1 — Pre-deploy checks\n```\n# Verify cluster context\nk8s_contexts()\n\n# Check current pod state\nk8s_pods(namespace="{namespace}")\n\n# Check Helm chart status (if applicable)\nhelm_status(release="{app}", namespace="{namespace}")\n```\n\n## Phase 2 — Deploy\n```\n# Option A — Helm upgrade/install\nhelm_upgrade(\n    release="{app}",\n    chart="<chart-path-or-repo/chart>",\n    namespace="{namespace}",\n    set_values={{"image.tag": "{(image.split(':')[-1] if ':' in image else 'latest')}"}},\n)\n\n# Option B — kubectl set image (for existing deployments)\nshell_run(cmd="kubectl set image deployment/{app} {app}={image} -n {namespace}")\n```\n\n## Phase 3 — Watch rollout\n```\nk8s_rollout(\n    action="status",\n    name="{app}",\n    namespace="{namespace}",\n    timeout=300,\n)\n```\n\nIf the rollout stalls:\n```\nk8s_rollout(action="history", name="{app}", namespace="{namespace}")\nk8s_logs(namespace="{namespace}", selector="app={app}", tail=50)\n```\n\n## Phase 4 — Verify pods are healthy\n```\nk8s_pods(namespace="{namespace}")\n```\n\nConfirm:\n- All replicas in `Running` state\n- `READY` column shows all containers ready (e.g. `1/1` or `2/2`)\n- `RESTARTS` count is 0 (or not increasing)\n\n## Phase 5 — Check application logs\n```\nk8s_logs(namespace="{namespace}", selector="app={app}", tail=100)\n```\n\nLook for:\n- Startup errors or panics\n- Failed health/readiness probes\n- Database connection failures\n\n## Phase 6 — Network health check\n```\n# If the service exposes an HTTP endpoint:\nnet_health(url="http://<service-url>/health")\nnet_http(url="http://<service-url>/health", method="GET")\n```\n\n## Rollback procedure\n```\n# Helm rollback\nhelm_upgrade(action="rollback", release="{app}", namespace="{namespace}")\n\n# kubectl rollback\nshell_run(cmd="kubectl rollout undo deployment/{app} -n {namespace}")\n\n# Verify rollback\nk8s_rollout(action="status", name="{app}", namespace="{namespace}")\nk8s_pods(namespace="{namespace}")\n```\n\n## Checklist\n- [ ] Rollout completed with 0 errors\n- [ ] All pods Running and Ready\n- [ ] Health endpoint responding 200\n- [ ] No elevated restart count\n- [ ] Previous version rollback tested (optional)\n'''

def api_design(api_name: str, description: str) -> str:
    """Spec-first API design: OpenAPI spec → stub → implement → test.

    Args:
        api_name:    Short name for the API (e.g. 'payments-api', 'user-service')
        description: One-paragraph description of what the API does
    """
    return f'# API Design: `{api_name}`\n\n**Description:** {description}\n\nYou are following a spec-first approach. Write the contract before the code.\n\n## Phase 1 — Parse any existing spec or generate a new one\n```\n# Check if an OpenAPI spec already exists\nsearch_find_files(name="openapi*.yaml", paths=".")\nsearch_find_files(name="openapi*.json", paths=".")\nsearch_find_files(name="swagger*.yaml", paths=".")\n\n# If one exists, parse it:\nopenapi_parse(path="<spec-file>")\n```\n\nIf no spec exists, create `openapi.yaml` following this template:\n```yaml\nopenapi: "3.1.0"\ninfo:\n  title: "{api_name}"\n  version: "0.1.0"\n  description: "{description}"\npaths:\n  /health:\n    get:\n      summary: Health check\n      responses:\n        "200":\n          description: OK\n```\n\n## Phase 2 — Review and validate the spec\n```\nopenapi_parse(path="openapi.yaml")\n```\n\nVerify:\n- All paths have `operationId`\n- Request/response schemas are defined\n- Authentication scheme is documented\n- Error responses (400, 401, 404, 500) are included\n\n## Phase 3 — Generate stub / scaffold\n```\n# Use template scaffold for the server stub\ntemplate_scaffold(\n    template="api-stub",\n    output="{api_name}",\n    vars={{"api_name": "{api_name}", "spec": "openapi.yaml"}},\n)\n```\n\n## Phase 4 — Check project conventions\n```\nspecnative_context(action="read", document="conventions")\nspecnative_context(action="read", document="architecture")\nspecnative_context(action="read", document="stack")\n```\n\n## Phase 5 — Implement endpoints\nFor each path in the spec:\n```\n# Find related existing code\nsearch_grep(pattern="{api_name}", paths=".")\n\n# Check test coverage as you implement\ntest_coverage_report(action="summary")\n```\n\n## Phase 6 — Write and run tests\n```\n# Run tests\nnpm_run(script="test")              # Node.js\njava_maven(goal="test")             # Java\ngo_test(cwd=".")                    # Go\n\n# Review coverage\ntest_coverage_report(action="summary")\ntest_coverage_report(action="check", min=80)\n```\n\n## Phase 7 — Security review\n```\nsecurity_eslint(action="scan")      # JS/TS\nsecurity_spotbugs(action="scan", security_only=True)  # Java\nsecrets_scan()\n```\n\n## Phase 8 — Validate final spec matches implementation\n```\nopenapi_parse(path="openapi.yaml")\nnet_health(url="http://localhost:<port>/health")\nnet_http(url="http://localhost:<port>/openapi.json", method="GET")\n```\n\n## Checklist\n- [ ] OpenAPI spec committed to repo\n- [ ] All endpoints have request/response schema validation\n- [ ] Auth/AuthZ documented and implemented\n- [ ] Error responses standardised (RFC 7807 Problem Details recommended)\n- [ ] Test coverage ≥ 80%\n- [ ] No secrets or CVEs found\n'

def go_project_analysis(project_dir: str='.') -> str:
    """Comprehensive analysis of a Go project: build, test, lint, mod, and security.

    Args:
        project_dir: Root directory of the Go project (default: cwd)
    """
    return f'# Go Project Analysis: `{project_dir}`\n\n## 1. Module and dependency graph\n```\ngo_mod(action="tidy",   cwd="{project_dir}")\ngo_mod(action="verify", cwd="{project_dir}")\ngo_mod(action="graph",  cwd="{project_dir}")\n```\n\n## 2. Build\n```\ngo_build(cwd="{project_dir}")\n```\n\n## 3. Run tests with coverage\n```\ngo_test(cwd="{project_dir}", cover=True)\ntest_coverage_report(action="summary", cwd="{project_dir}")\ntest_coverage_report(action="check",   cwd="{project_dir}", min=80)\n```\n\n## 4. Linting (golangci-lint)\n```\nlint_golangci(cwd="{project_dir}")\n```\n\n## 5. Check for secrets in source\n```\nsecrets_scan(cwd="{project_dir}")\n```\n\n## 6. Dependency security (if using govulncheck / OWASP)\n```\nsecurity_owasp(action="scan", cwd="{project_dir}")\n```\n\n## 7. File and structure overview\n```\nfs_tree(path="{project_dir}", max_depth=4)\ncontext_repo_size(cwd="{project_dir}")\ncontext_summarize(cwd="{project_dir}")\n```\n\n## 8. Find open TODOs and FIXMEs\n```\nsearch_todo(paths="{project_dir}")\n```\n\n## 9. Recent changes\n```\ngit_log(limit=10, cwd="{project_dir}")\ncontext_diff_summary(cwd="{project_dir}")\n```\n\n## Summary expectations\nAfter running the above, you should have:\n- Module dependency tree (flag any `replace` directives)\n- Build success / failure\n- Test pass rate and coverage percentage\n- Lint findings (treat `errcheck` and `govet` as blocking)\n- Known CVEs in dependencies\n- TODO/FIXME count and locations\n'

def performance_analysis(target: str) -> str:
    """Analyse performance: process top + ports + resource usage + profiling guide.

    Args:
        target: Process name, URL, or component to profile (e.g. 'my-api', 'http://localhost:8080')
    """
    is_url = target.startswith('http://') or target.startswith('https://')
    http_block = ''
    if is_url:
        http_block = f'```\n# HTTP response time\nnet_http(url="{target}", method="GET")\n\n# Health check latency\nnet_health(url="{target}/health")\n```\n'
    return f'''# Performance Analysis: `{target}`\n\n## Phase 1 — System-level resource snapshot\n```\n# Top processes by CPU and memory\nprocess_top()\n\n# All listening ports and bound services\nprocess_ports(action="listen")\n\n# Full process list\nprocess_ps()\n```\n\n## Phase 2 — Identify the target process\n```\n# Find the process by name\nprocess_ps(filter="{(target if not is_url else target.split('//')[-1].split(':')[0])}")\n\n# Inspect it in detail\nprocess_inspect(name="{(target if not is_url else target.split('//')[-1].split(':')[0])}")\n```\n\n## Phase 3 — Network / HTTP performance\n{http_block}\n```\n# Ports in use by the target\nprocess_port(port=<target-port>)\n```\n\n## Phase 4 — Container performance (if applicable)\n```\ndocker_ps()\ndocker_inspect(container="<container-name>")\ndocker_logs(container="<container-name>", tail=200)\n```\n\n## Phase 5 — Kubernetes resource usage (if applicable)\n```\nk8s_pods(namespace="<namespace>")\nk8s_logs(namespace="<namespace>", selector="app={target}", tail=100)\n```\n\n## Phase 6 — Application-level profiling guides\n\n### Go\n```go\nimport _ "net/http/pprof"\n// Then: go tool pprof http://localhost:<port>/debug/pprof/profile\n```\n```\nshell_run(cmd="go tool pprof -http=:8081 http://localhost:<port>/debug/pprof/heap")\n```\n\n### Java\n```\n# Enable JVM flight recorder / async-profiler\nshell_run(cmd="jcmd <pid> JFR.start duration=60s filename=recording.jfr")\njava_stacktrace(cwd=".")  # parse any existing thread dump\n```\n\n### Node.js\n```\nshell_run(cmd="node --inspect <entry-point>")\n# Connect Chrome DevTools to chrome://inspect\n```\n\n## Phase 7 — Identify bottlenecks\n```\n# Check for slow queries (if db is involved)\ndb_query(query="SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10", database="<db>")\n\n# Review recent git changes for perf regressions\ngit_log(limit=20)\ncontext_diff_summary()\n```\n\n## Performance checklist\n- [ ] CPU usage under load identified (top consumers)\n- [ ] Memory usage stable (no leak trend)\n- [ ] Response time P50/P95 measured\n- [ ] No port conflicts or connection exhaustion\n- [ ] Database query times acceptable\n- [ ] Profiling data collected for hotspots\n'''

def conventional_commit(type: str, description: str, scope: str='', body: str='', breaking_change: str='', issue: str='', cwd: str='.') -> str:
    """Craft and apply a Conventional Commit following the CC spec (conventionalcommits.org).

    Inspects staged changes, validates the commit message, and calls git_commit.

    Args:
        type:            Commit type — feat | fix | docs | style | refactor | perf | test | build | ci | chore | revert
        description:     Short imperative summary (≤ 72 chars minus type+scope prefix)
        scope:           Optional scope in parentheses — e.g. auth, api, db (default: none)
        body:            Optional body explaining WHY (leave blank to skip)
        breaking_change: Optional BREAKING CHANGE description (triggers MAJOR semver bump)
        issue:           Optional issue reference, e.g. '42' → 'Fixes #42'
        cwd:             Repository directory (default: cwd)
    """
    valid_types = list(_CC_TYPES)
    is_breaking = bool(breaking_change)
    scope_str = f'({scope})' if scope else ''
    bang = '!' if is_breaking else ''
    subject = f'{type}{scope_str}{bang}: {description}'
    footer_lines: list[str] = []
    if breaking_change:
        footer_lines.append(f'BREAKING CHANGE: {breaking_change}')
    if issue:
        footer_lines.append(f'Fixes #{issue}')
    footer = '\n'.join(footer_lines)
    warnings: list[str] = []
    if type not in valid_types:
        warnings.append(f"⚠️  `{type}` is not a standard CC type. Valid: {', '.join(valid_types)}")
    if len(subject) > 72:
        warnings.append(f'⚠️  Subject is {len(subject)} chars — keep it ≤ 72')
    warning_block = '\n' + '\n'.join(warnings) + '\n' if warnings else ''
    body_section = f'\n{body}' if body else ''
    footer_section = f'\n{footer}' if footer else ''
    full_message = f'{subject}{body_section}{footer_section}'
    types_table = ''.join((f'| `{t}` | {d} |\n' for (t, d) in _CC_TYPES.items()))
    return f'# Conventional Commit: `{subject}`\n{warning_block}\n## Commit message preview\n\n```\n{full_message}\n```\n\n## Step 1 — Verify staged changes\n\n```\ngit_status(cwd="{cwd}")\ngit_diff(staged=True, cwd="{cwd}")\n```\n\nIf nothing is staged, stage your files first:\n```\nshell_run(cmd="git add <files>", cwd="{cwd}")\n```\n\n## Step 2 — Review the diff matches the type `{type}`\n\n| Type | What it covers |\n|------|---------------|\n{types_table}\n## Step 3 — Commit\n\n```\ngit_commit(\n    action="commit",\n    message={repr(full_message)},\n    cwd="{cwd}",\n)\n```\n\n## Step 4 — Verify\n\n```\ngit_log(limit=1, cwd="{cwd}")\n```\n\n## Conventional Commits format reference\n\n```\n{_CC_FORMAT}\n```\n\n### Rules\n{_CC_RULES}\n'

def commit_amend(new_type: str='', new_scope: str='', new_description: str='', add_staged: bool=False, cwd: str='.') -> str:
    """Amend the last commit: fix the message and/or add forgotten staged files.

    Use this when you just committed and realized the message is wrong or you
    forgot to stage a file. Do NOT use on commits already pushed to a shared branch.

    Args:
        new_type:        New CC type (leave blank to keep current)
        new_scope:       New scope (leave blank to keep current)
        new_description: New description (leave blank to keep current)
        add_staged:      True if you have additional staged changes to fold in
        cwd:             Repository directory (default: cwd)
    """
    change_msg = bool(new_type or new_description)
    new_subject = ''
    if change_msg:
        scope_str = f'({new_scope})' if new_scope else ''
        new_subject = f'{new_type}{scope_str}: {new_description}'
    types_table = ''.join((f'| `{t}` | {d} |\n' for (t, d) in _CC_TYPES.items()))
    return f'''# Amend Last Commit\n\n⚠️  **Only amend commits that have NOT been pushed to a shared/remote branch.**\nIf the commit is already on `origin`, prefer `git_commit(action="revert")` + new commit.\n\n## Step 1 — Inspect the last commit\n\n```\ngit_log(limit=1, cwd="{cwd}")\ngit_diff(commit="HEAD~1..HEAD", cwd="{cwd}")\n```\n\n## Step 2 — Check what is currently staged\n\n```\ngit_status(cwd="{cwd}")\n```\n{('## Step 3 — Stage additional files to fold in' + chr(10) + '```' + chr(10) + f'git_status(cwd="{cwd}")' + chr(10) + '# Then stage missing files:' + chr(10) + f'shell_run(cmd="git add <forgotten-file>", cwd="{cwd}")' + chr(10) + '```' + chr(10) if add_staged else '')}\n## {('Step 4' if add_staged else 'Step 3')} — Amend\n\n{('**New subject:** `' + new_subject + '`' + chr(10) if new_subject else '_(Keeping the existing commit message — only folding in staged changes)_' + chr(10))}\n```\ngit_commit(\n    action="amend",\n{('    message=' + repr(new_subject) + ',' + chr(10) if new_subject else '')}    cwd="{cwd}",\n)\n```\n\n## {('Step 5' if add_staged else 'Step 4')} — Verify\n\n```\ngit_log(limit=2, cwd="{cwd}")\ngit_diff(commit="HEAD~1..HEAD", cwd="{cwd}")\n```\n\n## Conventional Commits type reference\n\n| Type | Use when… |\n|------|-----------|\n{types_table}\n'''

def commit_history_cleanup(base_branch: str='main', strategy: str='interactive', cwd: str='.') -> str:
    """Clean up commit history before opening a PR: squash WIP commits, fix messages.

    Strategies:
      interactive — shows all commits ahead of base, guides squash/reword one-by-one
      squash-all  — collapses all branch commits into a single conventional commit
      fixup       — applies all fixup! commits automatically

    Args:
        base_branch: The branch you will merge into (default: main)
        strategy:    interactive | squash-all | fixup (default: interactive)
        cwd:         Repository directory (default: cwd)
    """
    return f'''# Commit History Cleanup (before PR)\n\n**Base branch:** `{base_branch}`\n**Strategy:** `{strategy}`\n\n## Step 1 — See commits ahead of `{base_branch}`\n\n```\ngit_log(limit=30, cwd="{cwd}")\ncontext_diff_summary(since="{base_branch}", until="HEAD", cwd="{cwd}")\n```\n\nCount how many commits need cleaning. If the count is 1, nothing to do.\n\n## Step 2 — Verify there are no uncommitted changes\n\n```\ngit_status(cwd="{cwd}")\n```\n\nStage or stash anything uncommitted before rebasing.\n\n{('## Strategy: interactive rebase' + chr(10) + chr(10) + 'This lets you squash, reword, drop, or reorder commits one-by-one.' + chr(10) + chr(10) + '```' + chr(10) + f'# Rebase interactively against {base_branch}' + chr(10) + f'shell_run(cmd="git rebase -i {base_branch}", cwd="{cwd}")' + chr(10) + '```' + chr(10) + chr(10) + 'In the editor, change `pick` to:' + chr(10) + '- `r` / `reword` — keep commit but edit the message' + chr(10) + '- `s` / `squash` — merge into previous commit, edit combined message' + chr(10) + '- `f` / `fixup`  — merge into previous commit, discard this message' + chr(10) + '- `d` / `drop`   — remove the commit entirely' + chr(10) + chr(10) + 'After rebase completes:' + chr(10) + '```' + chr(10) + f'git_log(limit=10, cwd="{cwd}")' + chr(10) + '```' if strategy == 'interactive' else '')}\n{('## Strategy: squash-all' + chr(10) + chr(10) + f'Collapses all commits ahead of `{base_branch}` into one Conventional Commit.' + chr(10) + chr(10) + '```' + chr(10) + f'# Soft-reset to base (keeps all changes staged)' + chr(10) + f'shell_run(cmd="git reset --soft $(git merge-base HEAD {base_branch})", cwd="{cwd}")' + chr(10) + f'git_status(cwd="{cwd}")      # all changes now staged' + chr(10) + f'git_diff(staged=True, cwd="{cwd}")' + chr(10) + '```' + chr(10) + chr(10) + 'Then craft a single Conventional Commit covering all changes:' + chr(10) + '```' + chr(10) + '# Use the conventional_commit prompt for the merged change' + chr(10) + 'git_commit(' + chr(10) + '    action="commit",' + chr(10) + '    message="feat(scope): summarise all changes",' + chr(10) + f'    cwd="{cwd}",' + chr(10) + ')' + chr(10) + '```' if strategy == 'squash-all' else '')}\n{('## Strategy: fixup' + chr(10) + chr(10) + 'Automatically applies all `fixup!` commits to their targets.' + chr(10) + chr(10) + '```' + chr(10) + f'shell_run(cmd="git rebase --autosquash {base_branch}", cwd="{cwd}")' + chr(10) + f'git_log(limit=10, cwd="{cwd}")' + chr(10) + '```' if strategy == 'fixup' else '')}\n\n## Step 3 — Final validation\n\n```\ngit_log(limit=10, cwd="{cwd}")\ncontext_diff_summary(since="{base_branch}", until="HEAD", cwd="{cwd}")\n```\n\nAll commit messages should follow Conventional Commits:\n```\n{_CC_FORMAT}\n```\n\n### Rules\n{_CC_RULES}\n'''

def worktree_feature(feature: str, base_branch: str='main', worktree_base: str='../.claude/worktrees', cwd: str='.') -> str:
    """Isolate a single feature in its own git worktree (simpler than parallel workflow).

    Creates one worktree for focused work, then integrates via a PR.
    Use this for a single self-contained feature. For N parallel tasks use
    the `parallel_worktree_workflow` prompt instead.

    Args:
        feature:       Short slug for the feature (e.g. 'add-oauth', 'refactor-auth')
        base_branch:   Branch to branch from and PR into (default: main)
        worktree_base: Parent directory for worktrees (default: ../.claude/worktrees)
        cwd:           Main repository directory (default: cwd)
    """
    branch = f'feat/{feature}'
    wt_path = f'{worktree_base}/{feature}'
    commit_scope = feature.replace('-', '')
    return f'# Feature Worktree: `{feature}`\n\n**Branch:** `{branch}`\n**Worktree path:** `{wt_path}`\n**Base:** `{base_branch}`\n\n---\n\n## Phase 1 — Prepare\n\n```\n# Verify the repo is clean\ngit_status(cwd="{cwd}")\ngit_log(limit=5, cwd="{cwd}")\n\n# Check no existing worktree for this feature\ngit_worktree(action="list", cwd="{cwd}")\n```\n\nIf the worktree already exists, skip Phase 2 and go straight to Phase 3.\n\n---\n\n## Phase 2 — Create worktree\n\n```\ngit_worktree(\n    action="add",\n    path="{wt_path}",\n    branch="{branch}",\n    new_branch=True,\n    base="{base_branch}",\n    cwd="{cwd}",\n)\n```\n\nVerify it was created:\n```\ngit_worktree(action="list", cwd="{cwd}")\n```\n\n---\n\n## Phase 3 — Work in the worktree\n\nAll implementation happens inside `{wt_path}` — never in the main repo.\n\n```\n# Check context from the worktree\ngit_status(cwd="{wt_path}")\nfs_tree(path="{wt_path}", max_depth=3)\n\n# Read project conventions (SpecNative-aware repos)\nspecnative_context(action="read", document="conventions", cwd="{cwd}")\nspecnative_context(action="read", document="architecture", cwd="{cwd}")\n```\n\n### Development loop\n\n```\n# Inspect / search code\nsearch_grep(pattern="<keyword>", paths="{wt_path}")\n\n# After each logical unit — conventional commit\ngit_commit(\n    action="commit",\n    message="feat({commit_scope}): <describe what changed>",\n    cwd="{wt_path}",\n)\n```\n\nCommit often. Each commit should be a single logical change and follow\nConventional Commits (`feat`, `fix`, `test`, `refactor`, `docs`…).\n\n---\n\n## Phase 4 — Sync with `{base_branch}` (if it advanced)\n\n```\ngit_status(cwd="{wt_path}")\n\n# Rebase onto latest base\nshell_run(cmd="git fetch origin {base_branch} && git rebase origin/{base_branch}", cwd="{wt_path}")\n```\n\nResolve conflicts if any, then:\n```\nshell_run(cmd="git rebase --continue", cwd="{wt_path}")\n```\n\n---\n\n## Phase 5 — Pre-PR cleanup\n\n```\n# Review all commits ahead of base\ncontext_diff_summary(since="{base_branch}", until="HEAD", cwd="{wt_path}")\ngit_log(limit=20, cwd="{wt_path}")\n```\n\nSquash WIP commits using `commit_history_cleanup` prompt if needed.\n\n```\n# Run tests\njava_maven(goal="verify", cwd="{wt_path}")   # Java\ngo_test(cwd="{wt_path}")                      # Go\nnpm_run(script="test", cwd="{wt_path}")       # JS/TS\n\n# Check for secrets\nsecrets_scan(cwd="{wt_path}")\n```\n\n---\n\n## Phase 6 — Open PR\n\n```\n# Push the branch\nshell_run(cmd="git push -u origin {branch}", cwd="{wt_path}")\n\n# Create the PR\ngh_pr_create(\n    title="feat({commit_scope}): <one-line summary>",\n    body="## Summary\\n\\n- <bullet 1>\\n- <bullet 2>\\n\\n## Test plan\\n\\n- [ ] <test item>",\n    base="{base_branch}",\n    draft=False,\n)\n```\n\n---\n\n## Phase 7 — Cleanup after merge\n\n```\n# Remove worktree\ngit_worktree(action="remove", path="{wt_path}", cwd="{cwd}")\n\n# Delete local branch\nshell_run(cmd="git branch -d {branch}", cwd="{cwd}")\n\n# Verify\ngit_worktree(action="list", cwd="{cwd}")\ngit_branch(action="list", cwd="{cwd}")\n```\n'

def worktree_hotfix(hotfix: str, affected_version: str='', base_branch: str='main', worktree_base: str='../.claude/worktrees', cwd: str='.') -> str:
    """Emergency hotfix in an isolated worktree — minimal blast radius, fast turnaround.

    Creates a `hotfix/<name>` branch from `base_branch`, applies the fix in an
    isolated worktree, and opens a PR. Does NOT touch the main checkout.

    Args:
        hotfix:           Short slug for the issue (e.g. 'null-ptr-checkout', 'sql-injection-login')
        affected_version: Current production version affected (e.g. 'v2.3.1'), for the PR body
        base_branch:      Branch to hotfix from — usually main or a release branch (default: main)
        worktree_base:    Parent directory for worktrees (default: ../.claude/worktrees)
        cwd:              Main repository directory (default: cwd)
    """
    branch = f'hotfix/{hotfix}'
    wt_path = f'{worktree_base}/hotfix-{hotfix}'
    version_note = f' (affects `{affected_version}`)' if affected_version else ''
    return f'''# Emergency Hotfix: `{hotfix}`{version_note}\n\n**Branch:** `{branch}`\n**Worktree:** `{wt_path}`\n**Base:** `{base_branch}`\n\n⚠️  Hotfix rules:\n- Touch **only** the broken code. No refactoring, no new features.\n- Every change must be covered by a test.\n- PR must pass CI before merge.\n\n---\n\n## Phase 1 — Triage (understand the bug before touching anything)\n\n```\n# Current repo state\ngit_status(cwd="{cwd}")\ngit_log(limit=10, cwd="{cwd}")\n\n# Find the bug in code\nsearch_grep(pattern="<error keyword or class>", paths="{cwd}")\nsearch_todo(paths="{cwd}")\n\n# Check recent changes that might have introduced it\ncontext_diff_summary(since="{base_branch}~5", until="{base_branch}", cwd="{cwd}")\n```\n\nDocument the root cause before proceeding. Only continue once you understand\n**exactly** which file and line is broken.\n\n---\n\n## Phase 2 — Create isolated hotfix worktree\n\n```\ngit_worktree(\n    action="add",\n    path="{wt_path}",\n    branch="{branch}",\n    new_branch=True,\n    base="{base_branch}",\n    cwd="{cwd}",\n)\n\ngit_worktree(action="list", cwd="{cwd}")\n```\n\n---\n\n## Phase 3 — Apply the minimal fix\n\nWork exclusively inside `{wt_path}`:\n\n```\n# Confirm the bug is reproducible\njava_maven(goal="test -Dtest=<FailingTest>", cwd="{wt_path}")   # Java\ngo_test(pkg="./...", run="TestFailing", cwd="{wt_path}")         # Go\nnpm_run(script="test -- --grep '<failing test>'", cwd="{wt_path}")  # JS/TS\n```\n\nApply the fix, then:\n\n```\n# Verify fix passes\njava_maven(goal="test", cwd="{wt_path}")\ngo_test(cwd="{wt_path}")\nnpm_run(script="test", cwd="{wt_path}")\n\n# Security check (hotfixes are high-risk)\nsecrets_scan(cwd="{wt_path}")\nsecurity_spotbugs(action="scan", cwd="{wt_path}", security_only=True)\n```\n\n---\n\n## Phase 4 — Commit\n\nUse `fix:` type. Include issue reference in footer if available.\n\n```\ngit_commit(\n    action="commit",\n    message="fix({hotfix}): <concise description of what was broken and how it was fixed>\\n\\nRoot cause: <one sentence>\\n\\nFixes #<issue-number>",\n    cwd="{wt_path}",\n)\n\ngit_log(limit=3, cwd="{wt_path}")\ngit_diff(commit="{base_branch}..HEAD", cwd="{wt_path}")\n```\n\n---\n\n## Phase 5 — Open PR (mark as high priority)\n\n```\nshell_run(cmd="git push -u origin {branch}", cwd="{wt_path}")\n\ngh_pr_create(\n    title="fix({hotfix}): <concise summary>{version_note}",\n    body="## 🚨 Hotfix{version_note}\\n\\n## Root cause\\n<one paragraph>\\n\\n## Fix\\n<what changed and why it's safe>\\n\\n## Test plan\\n- [ ] Unit test added for the broken case\\n- [ ] Existing test suite passes\\n- [ ] Manually verified in staging",\n    base="{base_branch}",\n    draft=False,\n)\n```\n\n---\n\n## Phase 6 — Monitor CI\n\n```\ngh_actions(limit=3)\n```\n\nIf CI fails:\n```\ngh_actions_logs(action="failed", run_id=<run-id>)\n```\n\n---\n\n## Phase 7 — Post-merge cleanup\n\n```\ngit_worktree(action="remove", path="{wt_path}", cwd="{cwd}")\nshell_run(cmd="git branch -d {branch}", cwd="{cwd}")\ngit_worktree(action="list", cwd="{cwd}")\n```\n\nIf the hotfix needs to be back-ported to a release branch:\n```\ngit_cherry_pick(commit="<fix-sha>", cwd="{cwd}")\n```\n'''

def pr_create_flow(title: str, base_branch: str='main', draft: bool=False, type: str='feat', scope: str='', issue: str='', cwd: str='.') -> str:
    """Complete flow to create a well-structured GitHub Pull Request.

    Checks branch state, cleans commit history, writes the PR body from the
    diff, and calls gh_pr_create with a conventional title.

    Args:
        title:       Short PR title (will be prefixed with CC type, e.g. 'feat(auth): <title>')
        base_branch: Target branch for the PR (default: main)
        draft:       Open as draft PR (default: False)
        type:        Conventional Commits type for the PR title (default: feat)
        scope:       Optional CC scope, e.g. auth, api, db
        issue:       GitHub issue number this PR closes (e.g. '42')
        cwd:         Repository directory (default: cwd)
    """
    scope_str = f'({scope})' if scope else ''
    cc_title = f'{type}{scope_str}: {title}'
    close_kw = f'Closes #{issue}' if issue else ''
    types_table = ''.join((f'| `{t}` | {d} |\n' for (t, d) in _CC_TYPES.items()))
    return f'''# Create Pull Request: `{cc_title}`\n\n**Target:** `{base_branch}`\n**Draft:** `{('yes' if draft else 'no')}`\n{('**Closes:** #' + issue if issue else '')}\n\n---\n\n## Step 1 — Verify branch and commits\n\n```\ngit_status(cwd="{cwd}")\ngit_branch(action="current", cwd="{cwd}")\ngit_log(limit=20, cwd="{cwd}")\n```\n\nConfirm you are **not** on `{base_branch}`. If you are, create a feature branch first:\n```\nshell_run(cmd="git checkout -b {type}/{scope or title.lower().replace(' ', '-')}", cwd="{cwd}")\n```\n\n---\n\n## Step 2 — Inspect what will go into the PR\n\n```\ncontext_diff_summary(since="{base_branch}", until="HEAD", cwd="{cwd}")\ngit_diff(commit="{base_branch}..HEAD", cwd="{cwd}")\n```\n\nUse the diff to draft the PR body (Phases 4–5 below).\n\n---\n\n## Step 3 — Clean commit history (optional but recommended)\n\nIf there are WIP or fixup commits, use `commit_history_cleanup` first:\n```\n# squash WIP into clean conventional commits\n# see: commit_history_cleanup(base_branch="{base_branch}", strategy="interactive")\n```\n\nAll commits should follow Conventional Commits before opening the PR.\n\n---\n\n## Step 4 — Pre-flight checks\n\n```\n# No uncommitted changes\ngit_status(cwd="{cwd}")\n\n# Tests pass\njava_maven(goal="verify", cwd="{cwd}")      # Java\ngo_test(cwd="{cwd}")                         # Go\nnpm_run(script="test", cwd="{cwd}")          # JS/TS\n\n# No secrets\nsecrets_scan(cwd="{cwd}")\n\n# Lint clean\nlint_eslint(cwd="{cwd}")\nlint_pylint(cwd="{cwd}")\nlint_checkstyle(cwd="{cwd}")\n```\n\n---\n\n## Step 5 — Push branch\n\n```\nshell_run(cmd="git push -u origin HEAD", cwd="{cwd}")\n```\n\n---\n\n## Step 6 — Open the PR\n\n```\ngh_pr_create(\n    title="{cc_title}",\n    body="""## Summary\n\n- <bullet: what changed>\n- <bullet: why it was needed>\n- <bullet: any trade-offs>\n\n## Changes\n\n<!-- Auto-populated from diff — fill in from context_diff_summary output -->\n| File | Change |\n|------|--------|\n| `<file>` | <what changed> |\n\n## Test plan\n\n- [ ] Unit tests added / updated\n- [ ] Integration tests pass\n- [ ] Manually tested: <describe scenario>\n- [ ] No regressions in existing tests\n\n## Screenshots / logs (if applicable)\n\n<!-- paste output, screenshots, or benchmark numbers -->\n{close_kw}""",\n    base="{base_branch}",\n    draft={('True' if draft else 'False')},\n)\n```\n\n---\n\n## Step 7 — Post-creation\n\n```\n# Confirm PR was created\ngh_pr_list(state="open")\n\n# Check CI triggered\ngh_actions(limit=3)\n```\n\nAdd reviewers or labels via:\n```\nshell_run(cmd="gh pr edit --add-reviewer <username> --add-label <label>", cwd="{cwd}")\n```\n\n---\n\n## PR title conventions (Conventional Commits)\n\n| Type | When to use |\n|------|-------------|\n{types_table}\n'''

def pr_stack(stack: str, base_branch: str='main', cwd: str='.') -> str:
    """Manage a stack of dependent Pull Requests (stacked PRs / PR chains).

    Use stacked PRs when a large change is easier to review in layers:
      A (base) → B (depends on A) → C (depends on B)

    Each PR is small, focused, and independently reviewable.

    Args:
        stack:       Comma-separated PR names in dependency order, e.g. 'db-schema,api-layer,ui-layer'
        base_branch: The final landing branch (default: main)
        cwd:         Repository directory (default: cwd)
    """
    layers = [s.strip() for s in stack.split(',') if s.strip()]
    if not layers:
        layers = ['layer-1', 'layer-2', 'layer-3']
    branches = [base_branch] + [f'feat/{l}' for l in layers]
    branch_tree = '\n'.join((f"  {'  ' * i}`{branches[i]}` ← `{branches[i + 1]}`" for i in range(len(layers))))
    create_steps = ''
    for (i, layer) in enumerate(layers):
        parent = branches[i]
        current = branches[i + 1]
        create_steps += f'''### PR {i + 1}: `{current}` → `{parent}`\n\n```\nshell_run(cmd="git checkout {current}", cwd="{cwd}")\nshell_run(cmd="git push -u origin {current}", cwd="{cwd}")\n\ngh_pr_create(\n    title="feat({layer}): <describe this layer>",\n    body="Part {i + 1}/{len(layers)} of stack: `{stack}`\\n\\n## Summary\\n- <what this layer does>\\n\\n## Dependencies\\n- Depends on: #{('{PR_' + str(i) + '_NUMBER}' if i > 0 else 'none — this is the base PR')}",\n    base="{parent}",\n    draft={('True' if i < len(layers) - 1 else 'False')},\n)\n```\n\n'''
    update_steps = '\n'.join((f'shell_run(cmd="git checkout feat/{l} && git rebase feat/{(layers[i - 1] if i > 0 else base_branch)}", cwd="{cwd}")' for (i, l) in enumerate(layers)))
    return f'# Stacked PRs: `{stack}`\n\n**Stack depth:** {len(layers)}\n**Landing branch:** `{base_branch}`\n\n## Dependency tree\n\n```\n{base_branch} (final target)\n{branch_tree}\n```\n\nEach PR targets the branch **below** it in the stack, NOT `{base_branch}` directly.\nGitHub will show the correct diff for each layer.\n\n---\n\n## Phase 1 — Create branches\n\n```\n# Start from base\nshell_run(cmd="git checkout {base_branch} && git pull", cwd="{cwd}")\n```\n\n' + '\n'.join((f'```\nshell_run(cmd="git checkout -b feat/{l} {branches[i]}", cwd="{cwd}")\n```\n' for (i, l) in enumerate(layers))) + f'''\n\n---\n\n## Phase 2 — Implement each layer (bottom-up)\n\nWork on `feat/{layers[0]}` first, commit, then `feat/{layers[1]}`, etc.\nEach layer should contain only the changes relevant to its concern.\n\n```\n# For each layer:\ngit_status(cwd="{cwd}")\ngit_commit(action="commit", message="feat(<layer>): <description>", cwd="{cwd}")\n```\n\n---\n\n## Phase 3 — Open PRs (bottom-up, base PR first)\n\n{create_steps}\n\n---\n\n## Phase 4 — Update stack after review feedback\n\nIf `feat/{layers[0]}` changes after review, rebase all dependent layers:\n\n```\n{update_steps}\n```\n\nThen force-push each updated branch:\n```\n{''.join((f'shell_run(cmd="git push --force-with-lease origin feat/{l}", cwd="{cwd}")' + chr(10) for l in layers))}\n```\n\n---\n\n## Phase 5 — Merge in order (base first)\n\nMerge bottom-up. After each merge, GitHub automatically re-targets the next PR.\n\n```\n# Merge PR 1 (feat/{layers[0]} → {base_branch})\ngh_pr_merge(number=<PR_1_NUMBER>, method="squash")\n\n# GitHub now retargets PR 2 to {base_branch} — verify:\ngh_pr_list(state="open")\n\n# Merge PR 2, then PR 3…\n```\n\n---\n\n## Phase 6 — Cleanup\n\n```\n{''.join((f'shell_run(cmd="git branch -d feat/{l}", cwd="{cwd}")' + chr(10) for l in layers))}\ngit_branch(action="list", cwd="{cwd}")\n```\n\n---\n\n## Stacked PR rules\n\n- Each PR = one concern (schema | API | UI — not all three)\n- Commit messages follow Conventional Commits in every layer\n- Keep each PR ≤ 400 lines of diff — reviewers lose context above that\n- Mark all but the base PR as **draft** until the base is approved\n- Update the entire stack every time the base branch advances\n'''

def best_practice_commits(cwd: str='.', remote: str='origin', branch: str='', include_untracked: bool=False) -> str:
    """Analiza todos los cambios del repo, propone el plan de commits siguiendo
    Conventional Commits y espera confirmación del usuario antes de ejecutar.

    Flujo:
      1. Inspecciona status + diff completo (staged, unstaged, opcionalmente untracked)
      2. Agrupa los cambios por concern siguiendo las reglas de buenas prácticas
      3. Presenta el plan: N commits con mensaje CC + lista de archivos
      4. **Pausa y pregunta** al usuario si está de acuerdo
      5. Ejecuta sólo tras confirmación explícita (stage por grupos → commit → push opcional)

    Args:
        cwd:               Directorio del repositorio (default: cwd actual)
        remote:            Remote al que se hará push si el usuario confirma (default: origin)
        branch:            Rama a pushear (vacío = rama actual)
        include_untracked: Incluir archivos sin trackear en el análisis (default: False)
    """
    branch_note = f'`{branch}`' if branch else 'la rama actual'
    push_target = f'{remote} {branch}' if branch else f'{remote} HEAD'
    if include_untracked:
        untracked_block = f'```\n# 1e. Archivos sin trackear\nshell_run(cmd="git ls-files --others --exclude-standard", cwd="{cwd}")\n```'
    else:
        untracked_block = '_(Archivos sin trackear excluidos. Pasa `include_untracked=True` para incluirlos.)_'
    types_table = ''.join((f'| `{t}` | {d} |\n' for (t, d) in _CC_TYPES.items()))
    since_ref = f'origin/{branch}' if branch else 'HEAD~1'
    return f'# Best-Practice Commits\n\nAnaliza los cambios locales, propón un plan de commits con Conventional Commits\ny **pide confirmación antes de ejecutar nada**.\n\n---\n\n## FASE 1 — Recopilar cambios\n\nEjecuta estas herramientas en orden:\n\n```\n# 1a. Estado general\ngit_status(cwd="{cwd}")\n```\n\n```\n# 1b. Diff de cambios staged (si los hay)\ngit_diff(staged=True, cwd="{cwd}")\n```\n\n```\n# 1c. Diff de cambios unstaged\ngit_diff(cwd="{cwd}")\n```\n\n```\n# 1d. Historial reciente para entender el contexto\ngit_log(limit=10, cwd="{cwd}")\n```\n\n{untracked_block}\n\n---\n\n## FASE 2 — Analizar y agrupar\n\nCon la información recopilada, aplica estas reglas para agrupar los archivos en commits:\n\n### Reglas de agrupación\n{_GROUPING_RULES}\n\n### Señales por tipo de archivo\n{_GROUPING_FILE_SIGNALS}\n\n### Algoritmo de decisión\n\n```\nPara cada archivo modificado:\n  1. ¿Es config/CI/build? → grupo "infra" (ci:/build:/chore:)\n  2. ¿Es doc/md? → grupo "docs" (docs:)\n  3. ¿Es test y tiene fuente relacionada cambiada? → mismo grupo que la fuente\n  4. ¿Es código de aplicación?\n     → ¿Corrige un bug? → grupo "fix" del módulo correspondiente\n     → ¿Añade funcionalidad? → grupo "feat" del módulo correspondiente\n  5. ¿Cruza módulos distintos? → split en grupos por módulo\n```\n\n---\n\n## FASE 3 — Construir el plan de commits\n\nTras aplicar el análisis, elabora un plan con este formato exacto:\n\n```\n════════════════════════════════════════════════════════\n PLAN DE COMMITS PROPUESTO\n════════════════════════════════════════════════════════\n\nCommit 1/N\n  Mensaje : feat(scope): descripción imperativa ≤ 72 chars\n  Archivos: [\n    path/al/archivo1.py\n    path/al/archivo2.py\n    tests/test_archivo1.py\n  ]\n  Motivo  : (una línea explicando por qué van juntos)\n\nCommit 2/N\n  Mensaje : fix(scope): descripción\n  Archivos: [\n    path/otro/archivo.py\n  ]\n  Motivo  : corrección independiente de la feature anterior\n\n...\n\nTotal: N commits | +X líneas | -Y líneas\nPush a: {remote}/{branch_note}\n════════════════════════════════════════════════════════\n```\n\n### Reglas del mensaje CC\n{_CC_RULES}\n\n---\n\n## FASE 4 — ⏸ PAUSA: pedir confirmación\n\n**Después de presentar el plan, DEBES preguntar explícitamente al usuario:**\n\n```\n¿Estás de acuerdo con este plan de N commit(s)?\n\nOpciones:\n  ✅  sí / yes / ok        → ejecutar el plan tal como está\n  ✏️   ajustar <número>     → modificar el mensaje o los archivos del commit N\n  ➕  split <número>        → dividir el commit N en dos\n  ➖  merge <n1> <n2>       → fusionar los commits N1 y N2\n  ❌  cancelar              → no hacer nada\n\nTu respuesta:\n```\n\n**No ejecutes ningún `git_commit` ni `shell_run` hasta recibir la respuesta.**\n\n---\n\n## FASE 5 — Ejecutar el plan aprobado\n\nPara cada commit en el orden propuesto:\n\n### 5a. Limpiar el staging area\n```\nshell_run(cmd="git reset HEAD", cwd="{cwd}")\n```\n\n### 5b. Por cada commit del plan (repite el bloque N veces)\n\n```\n# Stage SÓLO los archivos de este commit\nshell_run(cmd="git add <archivo1> <archivo2> ...", cwd="{cwd}")\n\n# Verificar que sólo están los archivos correctos\ngit_diff(staged=True, cwd="{cwd}")\n```\n\n```\n# Crear el commit\ngit_commit(\n    action="commit",\n    message="<mensaje del plan>",\n    cwd="{cwd}",\n)\n```\n\n```\n# Confirmar resultado antes del siguiente commit\ngit_log(limit=1, cwd="{cwd}")\n```\n\n### 5c. Verificar el resultado completo\n```\ngit_log(limit=10, cwd="{cwd}")\ncontext_diff_summary(since="{since_ref}", until="HEAD", cwd="{cwd}")\n```\n\n---\n\n## FASE 6 — ⏸ PAUSA: confirmar push\n\nAntes de hacer push, informa el estado y pregunta:\n\n```\nCommits creados:\n  <lista de los commits recién creados con sha corto y mensaje>\n\n¿Deseas hacer push a `{remote}/{branch_note}` ahora?\n\n  ✅  sí / yes / push  → ejecutar git push\n  ❌  no / cancelar    → terminar aquí (puedes hacer push manual después)\n\nTu respuesta:\n```\n\n---\n\n## FASE 7 — Push (sólo si se confirma)\n\n```\nshell_run(\n    cmd="git push {push_target}",\n    cwd="{cwd}",\n)\n```\n\nVerificar:\n```\ngit_log(limit=5, cwd="{cwd}")\ngh_actions(limit=2)\n```\n\n---\n\n## Referencia rápida de tipos CC\n\n| Tipo | Cuándo |\n|------|--------|\n{types_table}\n## Anti-patrones que debes evitar\n\n| ❌ Mal | ✅ Bien |\n|--------|---------|\n| `fix: varios arreglos y nueva feature` | Separa fix y feat en commits distintos |\n| `WIP`, `tmp`, `asdf` como mensaje | Mensaje descriptivo siempre |\n| Un commit con 20 archivos de 3 módulos | Agrupa por concern, divide por módulo |\n| `feat: update` | `feat(auth): add JWT refresh token rotation` |\n| Mezclar código y cambios de CI | `ci:` commit separado |\n| Olvidar el scope cuando hay varios módulos | `feat(payment):`, `fix(cart):`, etc. |\n'

def gitignore_setup(preset: str='all', cwd: str='.') -> str:
    """Audit and patch .gitignore for macOS metadata and Claude Code files.

    Reads the current .gitignore, identifies missing patterns, and applies
    the selected preset without duplicating existing entries.

    Args:
        preset: Pattern set to apply — 'macos' | 'claude' | 'all' (default)
        cwd:    Repository root to operate on (default: current directory)
    """
    preset_descriptions = {'macos': 'archivos de metadatos de macOS (._*, .DS_Store, .Trashes, etc.)', 'claude': 'archivos locales de Claude Code (.claude/ excepto config compartida)', 'all': 'macOS + Claude Code (recomendado)'}
    desc = preset_descriptions.get(preset, preset)
    return f'# Configurar .gitignore — preset: `{preset}`\n\n**Objetivo:** Agregar patrones para {desc} al `.gitignore` del repositorio en `{cwd}`.\n\n---\n\n## Paso 1 — Auditar el estado actual\n\nLee el resource para ver el contenido actual y los patrones faltantes:\n```\nforge://config/gitignore\n```\n\nO con la tool directamente en modo dry-run:\n```\nconfig_gitignore(preset="{preset}", dry_run=True, cwd="{cwd}")\n```\n\nRevisa la sección `missing_patterns` del resultado.\n\n---\n\n## Paso 2 — Aplicar los patrones faltantes\n\nSi hay patrones faltantes, aplícalos:\n```\nconfig_gitignore(preset="{preset}", dry_run=False, cwd="{cwd}")\n```\n\nEl tool es **idempotente** — no duplica líneas ya existentes.\n\n---\n\n## Paso 3 — Verificar el resultado\n\nConfirma que los patrones quedaron registrados:\n```\nforge://config/gitignore\n```\n\nVerifica que `fully_covered` sea `true` y `missing_patterns` esté vacío.\n\n---\n\n## Paso 4 — Commitear el cambio\n\n```\ngit_status(cwd="{cwd}")\ngit_commit(message="chore: add macOS + Claude Code gitignore patterns", cwd="{cwd}")\n```\n\n---\n\n## Referencia de patrones\n\n### macOS\n| Patrón | Qué ignora |\n|--------|-----------|\n| `._*` | Apple Double (metadatos de archivos) |\n| `.DS_Store` | Configuración de carpetas del Finder |\n| `.AppleDouble/` | Carpetas de metadatos legacy |\n| `.LSOverride` | Overrides de Launch Services |\n| `.Spotlight-V100` | Índice de Spotlight |\n| `.Trashes` | Archivos en papelera del volumen |\n\n### Claude Code\n| Patrón | Qué ignora |\n|--------|-----------|\n| `.claude/` | Todo el directorio (sesiones, memoria, worktrees) |\n| `!.claude/launch.json` | **Excepción**: config de servidores dev |\n| `!.claude/settings.json` | **Excepción**: config del proyecto |\n| `!.claude/CLAUDE.md` | **Excepción**: documentación para agentes |\n'

PROMPTS = {
    "start_feature": start_feature,
    "code_review": code_review,
    "security_audit": security_audit,
    "release_workflow": release_workflow,
    "debug_ci_failure": debug_ci_failure,
    "java_project_analysis": java_project_analysis,
    "repo_health_check": repo_health_check,
    "specnative_workflow": specnative_workflow,
    "specnative_init_project": specnative_init_project,
    "specnative_handoff": specnative_handoff,
    "specnative_plan_tasks": specnative_plan_tasks,
    "specnative_implement_task": specnative_implement_task,
    "specnative_close_initiative": specnative_close_initiative,
    "multi_repo_health": multi_repo_health,
    "new_tool_scaffold": new_tool_scaffold,
    "maven_dependency_research": maven_dependency_research,
    "parallel_worktree_workflow": parallel_worktree_workflow,
    "bug_investigation": bug_investigation,
    "database_migration": database_migration,
    "docker_debug": docker_debug,
    "dependency_upgrade": dependency_upgrade,
    "k8s_deploy": k8s_deploy,
    "api_design": api_design,
    "go_project_analysis": go_project_analysis,
    "performance_analysis": performance_analysis,
    "conventional_commit": conventional_commit,
    "commit_amend": commit_amend,
    "commit_history_cleanup": commit_history_cleanup,
    "worktree_feature": worktree_feature,
    "worktree_hotfix": worktree_hotfix,
    "pr_create_flow": pr_create_flow,
    "pr_stack": pr_stack,
    "best_practice_commits": best_practice_commits,
    "gitignore_setup": gitignore_setup,
}
