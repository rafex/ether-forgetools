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

    Follows the official SpecNative 9-step agent workflow sequence.

    Args:
        initiative: Short hyphenated name for the feature (e.g. 'user-auth')
        problem:    One-sentence description of the problem being solved
    """
    return f"""\
# Start Feature: `{initiative}`

**Problem:** {problem}

Sigue el flujo oficial SpecNative de 9 pasos. **No omitas pasos.**

---

## Paso 1 — Navegación (entry point)
```
# Lee el README.md del folder actual primero
fs_read(path="README.md")
```

## Paso 2 — Coherencia de iniciativa
```
specnative_context(action="read", document="roadmap")
```
Verifica que `{initiative}` sea coherente con las prioridades actuales.

## Paso 3 — Contexto mínimo
```
specnative_context(action="read", document="product")
specnative_context(action="read", document="architecture")
```
Carga SOLO lo necesario. No leas todo el repositorio.

## Paso 4 — Respetar decisiones previas
```
specnative_context(action="decisions")
```
Lee los DEC-XXXX antes de escribir una sola línea de spec.

## Paso 5 — Crear workspace aislado + spec
```
git_worktree(action="add", path="../.claude/worktrees/{initiative}",
             branch="ai/{initiative}", new_branch=True)

# Preview primero:
specnative_initiative(action="start", initiative="{initiative}",
                      problem="{problem}", owner="<owner>")
# Si el preview es correcto, escribir:
specnative_initiative(action="start", initiative="{initiative}",
                      problem="{problem}", owner="<owner>", write=True)
```

**Estados de spec válidos:** `draft` → `active` → `blocked` | `done` | `superseded`

## Paso 6 — Derivar tareas
```
specnative_context(action="read", document="conventions")
specnative_context(action="read", document="stack")

# Preview:
specnative_initiative(action="plan", initiative="{initiative}")
# Escribir:
specnative_initiative(action="plan", initiative="{initiative}", write=True)
```

**Estados de tarea válidos:** `todo` → `in_progress` → `blocked` | `done`

## Paso 7 — Implementar (workflows/IMPLEMENTATION.md)
```
specnative_initiative(action="implement", initiative="{initiative}")
# Devuelve: target_tasks, spec_summary, conventions, agent_sequence,
#           placement_test para decidir dónde documentar cada cosa
```

Actualiza cada tarea antes de comenzar y al terminar:
```
specnative_initiative(action="state", initiative="{initiative}",
                      task_id="TASK-...", state="in_progress", write=True)
# ... código ...
specnative_initiative(action="state", initiative="{initiative}",
                      task_id="TASK-...", state="done", write=True)
```

## Paso 8 — Registrar decisiones persistentes
Solo si el tradeoff SOBREVIVE a esta iniciativa:
```
specnative_initiative(
    action="decision",
    title="<título de la decisión>",
    context="<por qué fue necesaria esta decisión>",
    decision="<qué se decidió>",
    consequences="<trade-offs e impactos>",
    decision_state="proposed",   # luego: accepted | deprecated | replaced
    write=True
)
```
**Usa el placement_test** (devuelto por implement) para decidir si va en
DECISIONS.md o en otro documento.

## Paso 9 — Cerrar y actualizar trazabilidad
```
specnative_initiative(action="review", initiative="{initiative}")
# Cuando ready_to_close = true:
specnative_initiative(action="close", initiative="{initiative}", write=True)
# TRACEABILITY.md se actualiza automáticamente en close
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
    _SPEC_STATES     = "draft → active → blocked | done | superseded"
    _TASK_STATES     = "todo → in_progress → blocked | done"
    _DEC_STATES      = "proposed → accepted | deprecated | replaced"
    _PLACEMENT_BRIEF = (
        "¿Desaparece al terminar la iniciativa? → SPEC.md\n"
        "¿Debe respetarse en la próxima iniciativa? → DECISIONS.md\n"
        "¿Explica el producto? → PRODUCT.md  |  ¿Guía prioridad temporal? → ROADMAP.md\n"
        "¿Describe estructura del sistema? → ARCHITECTURE.md"
    )

    if action == "status":
        return f"""\
# SpecNative Status: `{initiative}`

## Estados válidos
- Spec:     `{_SPEC_STATES}`
- Tarea:    `{_TASK_STATES}`
- Decisión: `{_DEC_STATES}`

## 1. Salud del repositorio (valida los 17 archivos requeridos)
```
specnative_status(action="validate")
specnative_status(action="status")
specnative_status(action="list-specs")
```

## 2. Leer spec e estado de tareas
```
specnative_context(action="read-spec", initiative="{initiative}")
specnative_context(action="list-tasks", initiative="{initiative}")
```

## 3. Decisiones relevantes (tradeoffs persistentes)
```
specnative_context(action="decisions")
```

## Placement test (¿dónde va este contenido?)
```
{_PLACEMENT_BRIEF}
```
"""

    if action == "start":
        return f"""\
# SpecNative Start: `{initiative}`

Sigue la secuencia oficial de 9 pasos.

## 1. Navegación y coherencia
```
fs_read(path="README.md")
specnative_context(action="read", document="roadmap")
```

## 2. Contexto mínimo + decisiones previas
```
specnative_context(action="read", document="product")
specnative_context(action="read", document="architecture")
specnative_context(action="decisions")
```

## 3. Crear spec (estado inicial: `draft`)
```
# Preview:
specnative_initiative(action="start", initiative="{initiative}",
                      problem="<describe the problem>", owner="<owner>")
# Escribir:
specnative_initiative(action="start", initiative="{initiative}",
                      problem="<describe the problem>", owner="<owner>", write=True)
```

## 4. Derivar tareas (estado inicial de cada tarea: `todo`)
```
specnative_context(action="read", document="conventions")
# Preview:
specnative_initiative(action="plan", initiative="{initiative}")
# Escribir:
specnative_initiative(action="plan", initiative="{initiative}", write=True)
```

## 5. Activar spec al comenzar implementación
```
specnative_initiative(action="state", initiative="{initiative}",
                      state="active", write=True)
```
"""

    if action == "implement":
        return f"""\
# SpecNative Implement: `{initiative}`

## 1. Cargar contexto de implementación (9-step sequence incluida)
```
specnative_initiative(action="implement", initiative="{initiative}")
```
El resultado incluye:
- `target_tasks` — tareas en estado `todo` o `in_progress`
- `spec_summary`, `conventions`, `architecture`, `stack`
- `agent_sequence` — los 9 pasos oficiales
- `placement_test` — árbol de decisiones sobre dónde documentar

## 2. Por cada tarea, ciclo: todo → in_progress → done
```
# Al comenzar:
specnative_initiative(action="state", initiative="{initiative}",
                      task_id="TASK-...", state="in_progress", write=True)

# Buscar código relacionado:
search_grep(pattern="<clase o función relevante>")
fs_find_by_type(extensions=".java,.py,.ts")

# Al terminar:
specnative_initiative(action="state", initiative="{initiative}",
                      task_id="TASK-...", state="done", write=True)
```

## 3. Si una tarea se bloquea
```
specnative_initiative(action="state", initiative="{initiative}",
                      task_id="TASK-...", state="blocked", write=True)
# Documentar el bloqueo en el SPEC.md con --state blocked
specnative_initiative(action="state", initiative="{initiative}",
                      state="blocked", write=True)
```

## 4. Registrar decisiones persistentes (usar placement_test)
```
# Solo si el tradeoff SOBREVIVE a esta iniciativa:
specnative_initiative(
    action="decision",
    title="<título>",
    context="<por qué>",
    decision="<qué se decidió>",
    consequences="<impactos>",
    decision_state="proposed",
    write=True
)
```
**Placement test rápido:**
```
{_PLACEMENT_BRIEF}
```
"""

    if action == "review":
        return f"""\
# SpecNative Review: `{initiative}`

## 1. Verificar que todas las tareas estén en `done`
```
specnative_initiative(action="review", initiative="{initiative}")
# ready_to_close debe ser true para continuar
```

## 2. Verificar tests
```
java_maven(goal="verify")
go_test()
npm_run(script="test")
```

## 3. Seguridad y calidad
```
secrets_scan()
security_spotbugs(action="scan", security_only=True)
lint_checkstyle()
lint_eslint()
lint_pylint()
```

## 4. Confirmar estado del spec
El spec debe estar en `active`. Si todo está bien, pasar a `close`.
"""

    if action == "close":
        return f"""\
# SpecNative Close: `{initiative}`

## 1. Revisión final
```
specnative_initiative(action="review", initiative="{initiative}")
# ready_to_close debe ser true
```

## 2. Registrar decisiones finales que sobrevivan (si aplica)
```
# Usa el placement_test para confirmar que va en DECISIONS.md:
# "¿Debe respetarse en la próxima iniciativa?" → sí → DECISIONS.md
specnative_initiative(
    action="decision",
    title="<título>",
    context="<por qué>",
    decision="<qué se decidió>",
    consequences="<impactos>",
    decision_state="proposed",
    write=True
)
```

## 3. Cerrar el spec (estado → `done`, actualiza TRACEABILITY.md)

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
# RESOURCES — additional coverage (docker, process, gh, db, context, k8s, test)
# ─────────────────────────────────────────────────────────────────────────────

# ── forge://docker/containers ─────────────────────────────────────────────────

@server.resource("forge://docker/containers")
def resource_docker_containers() -> str:
    """Running Docker containers snapshot (equivalent to docker ps)."""
    try:
        data = _run_tool("docker ps")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://process/listening ─────────────────────────────────────────────────

@server.resource("forge://process/listening")
def resource_process_listening() -> str:
    """Snapshot of all listening ports on the local machine."""
    try:
        data = _run_tool("process ports", action="listen")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://gh/open-prs ───────────────────────────────────────────────────────

@server.resource("forge://gh/open-prs")
def resource_gh_open_prs() -> str:
    """Open pull requests for the current repository."""
    try:
        data = _run_tool("gh pr-list", state="open")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://gh/ci-status ─────────────────────────────────────────────────────

@server.resource("forge://gh/ci-status")
def resource_gh_ci_status() -> str:
    """Latest GitHub Actions workflow runs (last 3) for the current repository."""
    try:
        data = _run_tool("gh actions", limit=3)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://db/schema/{database} ─────────────────────────────────────────────

@server.resource("forge://db/schema/{database}")
def resource_db_schema(database: str) -> str:
    """Database schema snapshot (tables list) for the given database name.

    Examples:
      forge://db/schema/myapp_development
      forge://db/schema/postgres
    """
    try:
        data = _run_tool("db schema", action="tables", database=database)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://context/summary ───────────────────────────────────────────────────

@server.resource("forge://context/summary")
def resource_context_summary() -> str:
    """AI-readable codebase summary: structure, languages, and key patterns."""
    try:
        data = _run_tool("context summarize")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://git/branches ──────────────────────────────────────────────────────

@server.resource("forge://git/branches")
def resource_git_branches() -> str:
    """All branches with ahead/behind tracking information for the cwd repository."""
    try:
        data = _run_tool("git branch", action="list")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://k8s/pods ─────────────────────────────────────────────────────────

@server.resource("forge://k8s/pods")
def resource_k8s_pods() -> str:
    """Current Kubernetes pod status across all namespaces."""
    try:
        data = _run_tool("k8s pods")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── forge://test/coverage ─────────────────────────────────────────────────────

@server.resource("forge://test/coverage")
def resource_test_coverage() -> str:
    """Latest test coverage summary for the cwd project."""
    try:
        data = _run_tool("test coverage-report", action="summary")
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS — additional workflows (bug, db, docker, deps, k8s, api, go, perf)
# ─────────────────────────────────────────────────────────────────────────────

@server.prompt()
def bug_investigation(symptom: str, component: str = "") -> str:
    """Structured bug hunt: logs + git blame + stacktrace + grep.

    Args:
        symptom:   Short description of the observed bug (e.g. 'NullPointerException in checkout')
        component: Optional component/module name to focus the search (e.g. 'payment-service')
    """
    scope = f" in `{component}`" if component else ""
    path_hint = component if component else "."
    return f"""\
# Bug Investigation: `{symptom}`{scope}

You are systematically hunting the root cause of a bug.
Work through each phase **in order**, stopping early if you find the culprit.

## Phase 1 — Reproduce and observe
```
# Check current repo state
git_status()
git_log(limit=10)

# Find recent changes related to the component
context_diff_summary()
```

## Phase 2 — Search for the symptom in code and logs
```
# Grep for error message / keyword
search_grep(pattern="{symptom[:60]}", paths="{path_hint}")

# Search for TODOs or known issues
search_todo(paths="{path_hint}")
```

## Phase 3 — Parse any stacktraces
```
# If it is a Java service:
java_stacktrace(cwd="{path_hint}")

# Tail recent application logs
fs_tail(path="<log-file>", lines=100)
```

## Phase 4 — Blame and history
```
# Find the file most likely containing the bug, then:
git_blame(file="<suspect-file>")

# See what changed recently in that area
git_log(path="<suspect-file>", limit=20)
git_diff(ref="HEAD~5..HEAD", path="<suspect-file>")
```

## Phase 5 — Check environment
```
diag_health()
diag_env()
diag_port(port=<service-port>)
```

## Phase 6 — Run tests to confirm fix scope
```
# Run tests for the affected component
java_maven(goal="test -pl {path_hint}", cwd=".")   # Java
go_test(pkg="./{path_hint}/...")                   # Go
npm_run(script="test", cwd="{path_hint}")          # JS/TS
```

## Resolution checklist
- [ ] Root cause identified (file + line)
- [ ] Regression test added or updated
- [ ] Fix committed with reference to this symptom
- [ ] Related TODOs / tech-debt items created if needed
"""


@server.prompt()
def database_migration(migration_name: str, db_type: str = "postgresql") -> str:
    """Plan, create, test, and prepare rollback for a database migration.

    Args:
        migration_name: Descriptive name for the migration (e.g. 'add-user-roles-table')
        db_type:        Database engine: postgresql | mysql | sqlite (default: postgresql)
    """
    return f"""\
# Database Migration: `{migration_name}`

**Database:** {db_type}

## Phase 1 — Understand current schema
```
# View all current tables
db_schema(action="tables", database="<your-database>")

# View schema for tables you plan to modify
db_schema(action="describe", database="<your-database>", table="<table-name>")

# Check pending migrations
db_migrations(action="status")
```

## Phase 2 — Check migration history
```
db_migrations(action="list")
db_migrations(action="pending")
```

## Phase 3 — Plan the migration
Before writing SQL, answer:
- Which tables/columns change?
- Are there foreign key constraints?
- Will this lock tables? (large tables need online DDL)
- What is the rollback path?

```
# Preview the migration file location
db_migrations(action="create", name="{migration_name}", preview=True)
```

## Phase 4 — Create the migration
```
db_migrations(action="create", name="{migration_name}")
# Edit the generated file to add UP and DOWN SQL
```

Example UP migration (`{db_type}`):
```sql
-- UP
ALTER TABLE users ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'member';
CREATE INDEX idx_users_role ON users(role);

-- DOWN (rollback)
DROP INDEX IF EXISTS idx_users_role;
ALTER TABLE users DROP COLUMN role;
```

## Phase 5 — Validate and run
```
# Dry-run against a test/staging database first
db_migrations(action="run", dry_run=True)

# Apply the migration
db_migrations(action="run")

# Verify schema updated
db_schema(action="tables", database="<your-database>")
db_schema(action="describe", database="<your-database>", table="<affected-table>")
```

## Phase 6 — Smoke test
```
# Run a quick query to verify data integrity
db_query(query="SELECT COUNT(*) FROM <affected-table>", database="<your-database>")
```

## Phase 7 — Rollback plan (keep ready)
```
# If rollback needed:
db_migrations(action="rollback", steps=1)
db_schema(action="tables", database="<your-database>")
```

## Checklist
- [ ] Schema change reviewed for locking risk
- [ ] DOWN migration tested on a copy of production data
- [ ] Migration idempotent (can be run twice safely)
- [ ] Application code compatible with both old and new schema (if zero-downtime)
"""


@server.prompt()
def docker_debug(container_name: str) -> str:
    """Debug a failing Docker container: logs → inspect → exec → fix.

    Args:
        container_name: Name or ID of the Docker container to debug
    """
    return f"""\
# Docker Debug: `{container_name}`

## Phase 1 — Observe running containers
```
docker_ps()
```

## Phase 2 — Tail container logs
```
# Last 100 lines
docker_logs(container="{container_name}", tail=100)

# Follow logs for 30 seconds to catch transient errors
docker_logs(container="{container_name}", follow=True, timeout=30)
```

## Phase 3 — Inspect container configuration
```
docker_inspect(container="{container_name}")
```

Look for:
- `State.Status` — is it `running`, `exited`, or `restarting`?
- `State.ExitCode` — non-zero indicates a crash
- `State.OOMKilled` — true means the container ran out of memory
- `HostConfig.PortBindings` — are ports exposed correctly?
- `Mounts` — are volumes mounted at the expected paths?
- `Config.Env` — are environment variables set correctly?

## Phase 4 — Check environment and port availability
```
diag_health()
process_port(port=<expected-port>)
```

## Phase 5 — Exec into the container (if still running)
```
docker_exec(container="{container_name}", cmd="sh -c 'env && ps aux'")

# Check disk space inside container
docker_exec(container="{container_name}", cmd="df -h")

# Check if the expected binary/process is running
docker_exec(container="{container_name}", cmd="ps aux")
```

## Phase 6 — Review compose configuration (if applicable)
```
docker_compose(action="config")
docker_compose(action="ps")
```

## Phase 7 — Common fixes

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| ExitCode 1, no logs | Missing env var | Check `Config.Env`, add to compose |
| OOMKilled = true | Memory limit too low | Increase `mem_limit` in compose |
| Port already in use | Host port conflict | `process_port(port=X)` to find owner |
| Health check failing | Wrong endpoint/port | Review `Healthcheck` in inspect output |
| Volume not found | Path typo | Check `Mounts` section |

## Phase 8 — Rebuild if config changed
```
docker_build(context=".", tag="{container_name}:debug")
docker_compose(action="up", service="{container_name}", build=True)
```
"""


@server.prompt()
def dependency_upgrade(ecosystem: str = "", scope: str = "all") -> str:
    """Safely upgrade dependencies: audit → upgrade → test → verify.

    Args:
        ecosystem: 'npm' | 'maven' | 'gradle' | 'go' | 'cargo' | '' (auto-detect)
        scope:     'security' (CVEs only) | 'minor' (patch+minor) | 'all' (major too)
    """
    eco_hint = ecosystem or "auto-detected"
    return f"""\
# Dependency Upgrade: `{eco_hint}` (scope: {scope})

## Phase 1 — Audit current state
```
# JavaScript / Node.js
npm_audit(cwd=".")

# Java (Maven / Gradle)
security_owasp(action="scan", cwd=".")
security_owasp(action="report", cwd=".")

# Go modules
go_mod(action="tidy")
go_mod(action="verify")

# Rust / Cargo
cargo_check(cwd=".")
```

## Phase 2 — Identify outdated dependencies
```
# Node.js — list outdated packages
shell_run(cmd="npm outdated --json")

# Maven — display available updates
java_maven(goal="versions:display-dependency-updates")
java_maven(goal="versions:display-plugin-updates")

# Go — list available upgrades
shell_run(cmd="go list -u -m all")

# Cargo
shell_run(cmd="cargo outdated")
```

## Phase 3 — Upgrade (adjust scope as needed)

### Security fixes only (`scope=security`)
```
# Node.js
npm_audit(action="fix", cwd=".")

# Maven: update only CVE-affected deps manually in pom.xml
java_maven_central(action="search", query="<vulnerable-library>")
```

### Minor + patch updates (`scope=minor`)
```
# Node.js
shell_run(cmd="npm update")
npm_install(cwd=".")

# Maven
java_maven(goal="versions:use-latest-releases -DallowMajorUpdates=false")
java_maven(goal="versions:commit")

# Go
shell_run(cmd="go get -u ./... && go mod tidy")
```

### All updates including major (`scope=all`)
```
# Review each major bump carefully — breaking changes likely!
# Node.js
shell_run(cmd="npx npm-check-updates -u && npm install")

# Maven — manually update version properties in pom.xml
# then:
java_maven(goal="dependency:resolve")
```

## Phase 4 — Verify integrity
```
# Node.js
npm_audit(cwd=".")
npm_run(script="build", cwd=".")

# Java
java_maven(goal="verify", cwd=".")

# Go
go_build(cwd=".")
go_mod(action="verify")

# Rust
cargo_build(cwd=".")
cargo_test(cwd=".")
```

## Phase 5 — Run full test suite
```
npm_run(script="test", cwd=".")         # JS/TS
java_maven(goal="test", cwd=".")        # Java
go_test(cwd=".")                        # Go
cargo_test(cwd=".")                     # Rust
```

## Phase 6 — Scan for new vulnerabilities introduced
```
secrets_scan(cwd=".")
security_owasp(action="scan", cwd=".")
npm_audit(cwd=".")
```

## Checklist
- [ ] All CVEs resolved (no HIGH/CRITICAL remaining)
- [ ] All tests passing after upgrade
- [ ] Changelog / release notes reviewed for breaking changes
- [ ] Lock file committed (`package-lock.json`, `go.sum`, `Cargo.lock`)
"""


@server.prompt()
def k8s_deploy(app: str, image: str, namespace: str = "default") -> str:
    """Deploy an app to Kubernetes: deploy → rollout → verify → health check.

    Args:
        app:       Application/deployment name (e.g. 'my-api')
        image:     Full Docker image reference (e.g. 'ghcr.io/org/my-api:v1.2.3')
        namespace: Kubernetes namespace (default: default)
    """
    return f"""\
# Kubernetes Deploy: `{app}`

**Image:** `{image}`
**Namespace:** `{namespace}`

## Phase 1 — Pre-deploy checks
```
# Verify cluster context
k8s_contexts()

# Check current pod state
k8s_pods(namespace="{namespace}")

# Check Helm chart status (if applicable)
helm_status(release="{app}", namespace="{namespace}")
```

## Phase 2 — Deploy
```
# Option A — Helm upgrade/install
helm_upgrade(
    release="{app}",
    chart="<chart-path-or-repo/chart>",
    namespace="{namespace}",
    set_values={{"image.tag": "{image.split(":")[-1] if ":" in image else "latest"}"}},
)

# Option B — kubectl set image (for existing deployments)
shell_run(cmd="kubectl set image deployment/{app} {app}={image} -n {namespace}")
```

## Phase 3 — Watch rollout
```
k8s_rollout(
    action="status",
    name="{app}",
    namespace="{namespace}",
    timeout=300,
)
```

If the rollout stalls:
```
k8s_rollout(action="history", name="{app}", namespace="{namespace}")
k8s_logs(namespace="{namespace}", selector="app={app}", tail=50)
```

## Phase 4 — Verify pods are healthy
```
k8s_pods(namespace="{namespace}")
```

Confirm:
- All replicas in `Running` state
- `READY` column shows all containers ready (e.g. `1/1` or `2/2`)
- `RESTARTS` count is 0 (or not increasing)

## Phase 5 — Check application logs
```
k8s_logs(namespace="{namespace}", selector="app={app}", tail=100)
```

Look for:
- Startup errors or panics
- Failed health/readiness probes
- Database connection failures

## Phase 6 — Network health check
```
# If the service exposes an HTTP endpoint:
net_health(url="http://<service-url>/health")
net_http(url="http://<service-url>/health", method="GET")
```

## Rollback procedure
```
# Helm rollback
helm_upgrade(action="rollback", release="{app}", namespace="{namespace}")

# kubectl rollback
shell_run(cmd="kubectl rollout undo deployment/{app} -n {namespace}")

# Verify rollback
k8s_rollout(action="status", name="{app}", namespace="{namespace}")
k8s_pods(namespace="{namespace}")
```

## Checklist
- [ ] Rollout completed with 0 errors
- [ ] All pods Running and Ready
- [ ] Health endpoint responding 200
- [ ] No elevated restart count
- [ ] Previous version rollback tested (optional)
"""


@server.prompt()
def api_design(api_name: str, description: str) -> str:
    """Spec-first API design: OpenAPI spec → stub → implement → test.

    Args:
        api_name:    Short name for the API (e.g. 'payments-api', 'user-service')
        description: One-paragraph description of what the API does
    """
    return f"""\
# API Design: `{api_name}`

**Description:** {description}

You are following a spec-first approach. Write the contract before the code.

## Phase 1 — Parse any existing spec or generate a new one
```
# Check if an OpenAPI spec already exists
search_find_files(name="openapi*.yaml", paths=".")
search_find_files(name="openapi*.json", paths=".")
search_find_files(name="swagger*.yaml", paths=".")

# If one exists, parse it:
openapi_parse(path="<spec-file>")
```

If no spec exists, create `openapi.yaml` following this template:
```yaml
openapi: "3.1.0"
info:
  title: "{api_name}"
  version: "0.1.0"
  description: "{description}"
paths:
  /health:
    get:
      summary: Health check
      responses:
        "200":
          description: OK
```

## Phase 2 — Review and validate the spec
```
openapi_parse(path="openapi.yaml")
```

Verify:
- All paths have `operationId`
- Request/response schemas are defined
- Authentication scheme is documented
- Error responses (400, 401, 404, 500) are included

## Phase 3 — Generate stub / scaffold
```
# Use template scaffold for the server stub
template_scaffold(
    template="api-stub",
    output="{api_name}",
    vars={{"api_name": "{api_name}", "spec": "openapi.yaml"}},
)
```

## Phase 4 — Check project conventions
```
specnative_context(action="read", document="conventions")
specnative_context(action="read", document="architecture")
specnative_context(action="read", document="stack")
```

## Phase 5 — Implement endpoints
For each path in the spec:
```
# Find related existing code
search_grep(pattern="{api_name}", paths=".")

# Check test coverage as you implement
test_coverage_report(action="summary")
```

## Phase 6 — Write and run tests
```
# Run tests
npm_run(script="test")              # Node.js
java_maven(goal="test")             # Java
go_test(cwd=".")                    # Go

# Review coverage
test_coverage_report(action="summary")
test_coverage_report(action="check", min=80)
```

## Phase 7 — Security review
```
security_eslint(action="scan")      # JS/TS
security_spotbugs(action="scan", security_only=True)  # Java
secrets_scan()
```

## Phase 8 — Validate final spec matches implementation
```
openapi_parse(path="openapi.yaml")
net_health(url="http://localhost:<port>/health")
net_http(url="http://localhost:<port>/openapi.json", method="GET")
```

## Checklist
- [ ] OpenAPI spec committed to repo
- [ ] All endpoints have request/response schema validation
- [ ] Auth/AuthZ documented and implemented
- [ ] Error responses standardised (RFC 7807 Problem Details recommended)
- [ ] Test coverage ≥ 80%
- [ ] No secrets or CVEs found
"""


@server.prompt()
def go_project_analysis(project_dir: str = ".") -> str:
    """Comprehensive analysis of a Go project: build, test, lint, mod, and security.

    Args:
        project_dir: Root directory of the Go project (default: cwd)
    """
    return f"""\
# Go Project Analysis: `{project_dir}`

## 1. Module and dependency graph
```
go_mod(action="tidy",   cwd="{project_dir}")
go_mod(action="verify", cwd="{project_dir}")
go_mod(action="graph",  cwd="{project_dir}")
```

## 2. Build
```
go_build(cwd="{project_dir}")
```

## 3. Run tests with coverage
```
go_test(cwd="{project_dir}", cover=True)
test_coverage_report(action="summary", cwd="{project_dir}")
test_coverage_report(action="check",   cwd="{project_dir}", min=80)
```

## 4. Linting (golangci-lint)
```
lint_golangci(cwd="{project_dir}")
```

## 5. Check for secrets in source
```
secrets_scan(cwd="{project_dir}")
```

## 6. Dependency security (if using govulncheck / OWASP)
```
security_owasp(action="scan", cwd="{project_dir}")
```

## 7. File and structure overview
```
fs_tree(path="{project_dir}", max_depth=4)
context_repo_size(cwd="{project_dir}")
context_summarize(cwd="{project_dir}")
```

## 8. Find open TODOs and FIXMEs
```
search_todo(paths="{project_dir}")
```

## 9. Recent changes
```
git_log(limit=10, cwd="{project_dir}")
context_diff_summary(cwd="{project_dir}")
```

## Summary expectations
After running the above, you should have:
- Module dependency tree (flag any `replace` directives)
- Build success / failure
- Test pass rate and coverage percentage
- Lint findings (treat `errcheck` and `govet` as blocking)
- Known CVEs in dependencies
- TODO/FIXME count and locations
"""


@server.prompt()
def performance_analysis(target: str) -> str:
    """Analyse performance: process top + ports + resource usage + profiling guide.

    Args:
        target: Process name, URL, or component to profile (e.g. 'my-api', 'http://localhost:8080')
    """
    is_url = target.startswith("http://") or target.startswith("https://")
    return f"""\
# Performance Analysis: `{target}`

## Phase 1 — System-level resource snapshot
```
# Top processes by CPU and memory
process_top()

# All listening ports and bound services
process_ports(action="listen")

# Full process list
process_ps()
```

## Phase 2 — Identify the target process
```
# Find the process by name
process_ps(filter="{target if not is_url else target.split('//')[-1].split(':')[0]}")

# Inspect it in detail
process_inspect(name="{target if not is_url else target.split('//')[-1].split(':')[0]}")
```

## Phase 3 — Network / HTTP performance
{"" if not is_url else f"""```
# HTTP response time
net_http(url="{target}", method="GET")

# Health check latency
net_health(url="{target}/health")
```
"""}
```
# Ports in use by the target
process_port(port=<target-port>)
```

## Phase 4 — Container performance (if applicable)
```
docker_ps()
docker_inspect(container="<container-name>")
docker_logs(container="<container-name>", tail=200)
```

## Phase 5 — Kubernetes resource usage (if applicable)
```
k8s_pods(namespace="<namespace>")
k8s_logs(namespace="<namespace>", selector="app={target}", tail=100)
```

## Phase 6 — Application-level profiling guides

### Go
```go
import _ "net/http/pprof"
// Then: go tool pprof http://localhost:<port>/debug/pprof/profile
```
```
shell_run(cmd="go tool pprof -http=:8081 http://localhost:<port>/debug/pprof/heap")
```

### Java
```
# Enable JVM flight recorder / async-profiler
shell_run(cmd="jcmd <pid> JFR.start duration=60s filename=recording.jfr")
java_stacktrace(cwd=".")  # parse any existing thread dump
```

### Node.js
```
shell_run(cmd="node --inspect <entry-point>")
# Connect Chrome DevTools to chrome://inspect
```

## Phase 7 — Identify bottlenecks
```
# Check for slow queries (if db is involved)
db_query(query="SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10", database="<db>")

# Review recent git changes for perf regressions
git_log(limit=20)
context_diff_summary()
```

## Performance checklist
- [ ] CPU usage under load identified (top consumers)
- [ ] Memory usage stable (no leak trend)
- [ ] Response time P50/P95 measured
- [ ] No port conflicts or connection exhaustion
- [ ] Database query times acceptable
- [ ] Profiling data collected for hotspots
"""


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
