from __future__ import annotations

"""
specnative/_core.py — Shared helpers for SpecNative tools.

SpecNative repos support both the legacy ``agents/`` layout and the current
v0.9 ``spec-native/`` layout. The helper maps either layout to one API.
  AGENTS.md                          — operating contract (read first)
  agents/PRODUCT.md                  — user problems / vision
  agents/ARCHITECTURE.md             — system structure, boundaries
  agents/STACK.md                    — technology choices, versions, constraints
  agents/CONVENTIONS.md              — naming, style, testing rules
  agents/COMMANDS.md                 — project-specific build/run/test commands
  agents/DECISIONS.md                — persistent trade-offs (DEC-XXXX)
  agents/ROADMAP.md                  — temporal priorities and rationale
  agents/TRACEABILITY.md             — cross-artifact links
  agents/SPEC.md                     — default spec (agents domain)
  agents/specs/<initiative>/SPEC.md  — per-initiative specs
  tasks/<initiative>/TASKS.md        — per-initiative tasks
  workflows/PLANNING.md              — planning workflow guide
  workflows/IMPLEMENTATION.md        — implementation workflow guide
  workflows/REVIEW.md                — review workflow guide
  pipelines/CI.md                    — automated validation gates
  pipelines/CD.md                    — delivery process
  .specnative/SCHEMA.md              — TOML schema definition
  .specnative/CLI.md                 — CLI command reference

Principle: "Una verdad por documento" — each document owns one semantic
domain exclusively. README.md files are navigation indices, not sources
of truth. UPPERCASE files are agent context.
"""

from pathlib import Path
from typing import Any

# ── Required files (SpecNative contract) ─────────────────────────────────────

REQUIRED_FILES = [
    "AGENTS.md",
    "agents/PRODUCT.md",
    "agents/ARCHITECTURE.md",
    "agents/STACK.md",
    "agents/CONVENTIONS.md",
    "agents/COMMANDS.md",
    "agents/DECISIONS.md",
    "agents/ROADMAP.md",
    "agents/TRACEABILITY.md",
    "agents/SPEC.md",
    "workflows/PLANNING.md",
    "workflows/IMPLEMENTATION.md",
    "workflows/REVIEW.md",
    "pipelines/CI.md",
    "pipelines/CD.md",
    ".specnative/SCHEMA.md",
    ".specnative/CLI.md",
]

MODERN_REQUIRED_FILES = [
    "AGENTS.md",
    "spec-native/README.md",
    "spec-native/PRODUCT.md",
    "spec-native/ARCHITECTURE.md",
    "spec-native/STACK.md",
    "spec-native/CONVENTIONS.md",
    "spec-native/COMMANDS.md",
    "spec-native/DECISIONS.md",
    "spec-native/ROADMAP.md",
    "spec-native/TRACEABILITY.md",
    "spec-native/SESSION.md",
    "spec-native/specs/README.md",
    "spec-native/tasks/README.md",
    "spec-native/tasks/TASKS.template.md",
    "spec-native/architecture/README.md",
    "spec-native/conventions/README.md",
    "spec-native/decisions/README.md",
    "spec-native/backlog/README.md",
    "spec-native/intake/README.md",
    "spec-native/workflows/README.md",
    "spec-native/pipelines/README.md",
    ".specnative/SCHEMA.md",
    ".specnative/CLI.md",
    ".specnative/MCP.md",
]

# ── Context document map ──────────────────────────────────────────────────────

CONTEXT_MAP: dict[str, str] = {
    # core agent context
    "agents":           "AGENTS.md",
    "product":          "agents/PRODUCT.md",
    "architecture":     "agents/ARCHITECTURE.md",
    "stack":            "agents/STACK.md",
    "conventions":      "agents/CONVENTIONS.md",
    "commands":         "agents/COMMANDS.md",
    "decisions":        "agents/DECISIONS.md",
    "roadmap":          "agents/ROADMAP.md",
    "traceability":     "agents/TRACEABILITY.md",
    "spec":             "agents/SPEC.md",
    # workflows
    "planning":         "workflows/PLANNING.md",
    "implementation":   "workflows/IMPLEMENTATION.md",
    "review":           "workflows/REVIEW.md",
    # pipelines
    "ci":               "pipelines/CI.md",
    "cd":               "pipelines/CD.md",
    # framework meta
    "schema":           ".specnative/SCHEMA.md",
    "cli":              ".specnative/CLI.md",
}

MODERN_CONTEXT_MAP: dict[str, str] = {
    "agents":           "AGENTS.md",
    "product":          "spec-native/PRODUCT.md",
    "architecture":     "spec-native/ARCHITECTURE.md",
    "stack":            "spec-native/STACK.md",
    "conventions":      "spec-native/CONVENTIONS.md",
    "commands":         "spec-native/COMMANDS.md",
    "decisions":        "spec-native/DECISIONS.md",
    "roadmap":          "spec-native/ROADMAP.md",
    "traceability":     "spec-native/TRACEABILITY.md",
    "session":          "spec-native/SESSION.md",
    "spec":             "spec-native/SPEC.md",
    "planning":         "spec-native/workflows/PLANNING.md",
    "implementation":   "spec-native/workflows/IMPLEMENTATION.md",
    "review":           "spec-native/workflows/REVIEW.md",
    "ci":               "spec-native/pipelines/CI.md",
    "cd":               "spec-native/pipelines/CD.md",
    "schema":           ".specnative/SCHEMA.md",
    "cli":              ".specnative/CLI.md",
    "mcp":              ".specnative/MCP.md",
}

# ── Valid states (official SpecNative schema) ─────────────────────────────────

SPEC_STATES      = ("draft", "active", "blocked", "done", "superseded")
TASK_STATES      = ("todo", "in_progress", "blocked", "done")
DECISION_STATES  = ("proposed", "accepted", "deprecated", "replaced")

# ── Document ownership (decision placement test) ──────────────────────────────

DOCUMENT_OWNERSHIP: dict[str, dict] = {
    "PRODUCT.md": {
        "contains": ["Problem", "users", "objectives", "value proposition"],
        "excludes":  ["Implementation", "technical decisions"],
        "placement_test": "¿Explica el producto o el problema del usuario?",
    },
    "SPEC.md": {
        "contains": ["Requirements", "scope", "acceptance criteria", "risks"],
        "excludes":  ["Persistent tradeoffs", "product vision", "direction"],
        "placement_test": "¿Desaparece cuando termina la iniciativa?",
    },
    "DECISIONS.md": {
        "contains": ["Persistent tradeoffs for future initiatives"],
        "excludes":  ["What to build", "temporal priorities"],
        "placement_test": "¿Debe respetarse en la próxima iniciativa?",
    },
    "ROADMAP.md": {
        "contains": ["Temporal sequencing", "rationale"],
        "excludes":  ["Implementation approach", "specific tradeoffs"],
        "placement_test": "¿Guía la prioridad temporal?",
    },
    "ARCHITECTURE.md": {
        "contains": ["Modules", "boundaries", "data flows", "constraints"],
        "excludes":  ["What to build", "decision rationale"],
        "placement_test": "¿Describe la estructura del sistema?",
    },
    "STACK.md": {
        "contains": ["Languages", "runtimes", "frameworks", "versions"],
        "excludes":  ["Code structure", "conventions"],
        "placement_test": "¿Describe tecnologías y versiones?",
    },
    "CONVENTIONS.md": {
        "contains": ["Naming", "style", "testing approach", "commit rules"],
        "excludes":  ["Project commands", "technology choices"],
        "placement_test": "¿Guía cómo se escribe el código?",
    },
    "COMMANDS.md": {
        "contains": ["Build", "test", "lint", "run", "migrations"],
        "excludes":  ["Framework CLI commands"],
        "placement_test": "¿Son comandos específicos de este proyecto?",
    },
    "CI.md": {
        "contains": ["Automated gates", "triggers", "checks"],
        "excludes":  ["Local development", "implementation logic"],
        "placement_test": "¿Define validaciones automáticas de CI?",
    },
    "CD.md": {
        "contains": ["Release process", "environments", "promotion gates"],
        "excludes":  ["Deploy scripts", "credentials"],
        "placement_test": "¿Describe entrega a producción?",
    },
}

PLACEMENT_DECISION_TREE = [
    ("¿Desaparece cuando termina la iniciativa?",        "SPEC.md"),
    ("¿Debe respetarse en la próxima iniciativa?",       "DECISIONS.md"),
    ("¿Explica el producto o problema del usuario?",     "PRODUCT.md"),
    ("¿Guía la prioridad temporal?",                     "ROADMAP.md"),
    ("¿Describe la estructura del sistema?",             "ARCHITECTURE.md"),
    ("¿Describe tecnologías, versiones o constraints?",  "STACK.md"),
    ("¿Guía cómo se escribe el código?",                 "CONVENTIONS.md"),
    ("¿Son comandos de build/test/run de este proyecto?","COMMANDS.md"),
    ("¿Define validaciones automáticas de CI?",          "CI.md"),
    ("¿Describe la entrega a producción?",               "CD.md"),
]

# ── Agent workflow sequence (official 9-step) ─────────────────────────────────

AGENT_WORKFLOW_SEQUENCE = [
    "1. Leer README.md del folder actual (punto de entrada de navegación)",
    "2. Revisar ROADMAP.md para confirmar coherencia de la iniciativa",
    "3. Cargar contexto mínimo: PRODUCT.md + arquitectura relevante",
    "4. Estudiar DECISIONS.md para respetar tradeoffs persistentes",
    "5. Revisar o crear SPEC.md para la iniciativa",
    "6. Derivar o leer tasks/ (TASKS.md de la iniciativa)",
    "7. Implementar siguiendo workflows/IMPLEMENTATION.md",
    "8. Registrar en DECISIONS.md SOLO tradeoffs que sobreviven a esta iniciativa",
    "9. Actualizar TRACEABILITY.md al cerrar la iniciativa",
]


# ── File I/O ──────────────────────────────────────────────────────────────────

def read_file(root: Path, rel: str) -> str | None:
    """Read a file relative to root. Returns None if missing."""
    p = root / rel
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except Exception as e:
        return f"[ERROR reading {rel}: {e}]"


def uses_modern_layout(root: Path) -> bool:
    """Return True for SpecNative v0.6+ repositories using spec-native/."""
    return (root / "spec-native").is_dir()


def context_map_for(root: Path) -> dict[str, str]:
    return MODERN_CONTEXT_MAP if uses_modern_layout(root) else CONTEXT_MAP


def required_files_for(root: Path) -> list[str]:
    return MODERN_REQUIRED_FILES if uses_modern_layout(root) else REQUIRED_FILES


def context_rel(root: Path, document: str) -> str | None:
    mapping = context_map_for(root)
    return mapping.get(document)


def specs_dir(root: Path) -> Path:
    return root / "spec-native" / "specs" if uses_modern_layout(root) else root / "agents" / "specs"


def tasks_dir(root: Path) -> Path:
    return root / "spec-native" / "tasks" if uses_modern_layout(root) else root / "tasks"


def workflows_dir(root: Path) -> Path:
    return root / "spec-native" / "workflows" if uses_modern_layout(root) else root / "workflows"


def spec_path_for(root: Path, initiative: str | None = None) -> Path:
    if initiative:
        return specs_dir(root) / initiative / "SPEC.md"
    return root / "spec-native" / "SPEC.md" if uses_modern_layout(root) else root / "agents" / "SPEC.md"


def tasks_path_for(root: Path, initiative: str) -> Path:
    return tasks_dir(root) / initiative / "TASKS.md"


def read_context_document(root: Path, document: str) -> tuple[str | None, str | None]:
    rel = context_rel(root, document)
    if rel is None:
        return None, None
    return rel, read_file(root, rel)


# ── TOML parsing ──────────────────────────────────────────────────────────────

def _toml_loads(text: str) -> dict[str, Any]:
    """Parse first ```toml block found in text."""
    import re
    m = re.search(r"```toml\s*\n(.*?)```", text, re.DOTALL)
    if not m:
        return {}
    toml_str = m.group(1)
    try:
        try:
            import tomllib  # Python 3.11+
            return tomllib.loads(toml_str)
        except ImportError:
            try:
                import tomli as tomllib
                return tomllib.loads(toml_str)
            except ImportError:
                return _toml_fallback(toml_str)
    except Exception:
        return _toml_fallback(toml_str)


def _toml_fallback(text: str) -> dict[str, Any]:
    """Minimal hand-rolled TOML parser (key = value lines only)."""
    import re
    result: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            raw = v.strip()
            # array: ["a", "b"]
            arr_m = re.match(r'^\[(.*)\]$', raw)
            if arr_m:
                items = re.findall(r'"([^"]*)"', arr_m.group(1))
                result[k] = items
                continue
            result[k] = raw.strip('"').strip("'")
    return result


# ── Spec/Task discovery ───────────────────────────────────────────────────────

def find_specs(root: Path) -> list[Path]:
    """Find all SPEC.md files under root, excluding .specnative."""
    return sorted(
        p for p in root.rglob("SPEC.md")
        if ".specnative" not in p.parts
    )


def find_task_files(root: Path) -> list[Path]:
    """Find all TASKS.md files under the active SpecNative tasks directory."""
    base = tasks_dir(root)
    if not base.is_dir():
        return []
    return sorted(base.rglob("TASKS.md"))


def parse_spec(path: Path, root: Path) -> dict[str, Any]:
    """Read and parse a SPEC.md file."""
    text = path.read_text(encoding="utf-8")
    meta = _toml_loads(text)
    return {
        "_path": str(path.relative_to(root)),
        **meta,
    }


def parse_all_toml_blocks(text: str) -> list[dict[str, Any]]:
    """Parse ALL ```toml blocks in a file (task files have one per task)."""
    import re
    blocks = re.findall(r"```toml\s*\n(.*?)```", text, re.DOTALL)
    results = []
    for block in blocks:
        try:
            try:
                import tomllib
                results.append(tomllib.loads(block))
            except ImportError:
                results.append(_toml_fallback(block))
        except Exception:
            results.append(_toml_fallback(block))
    return results


def task_state_summary(task_file: Path) -> dict[str, int]:
    """Count task states in a TASKS.md file."""
    text = task_file.read_text(encoding="utf-8")
    tasks = parse_all_toml_blocks(text)
    counts: dict[str, int] = {}
    for t in tasks:
        state = t.get("state", "unknown")
        counts[state] = counts.get(state, 0) + 1
    return counts
