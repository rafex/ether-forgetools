from __future__ import annotations

"""
specnative/_core.py — Shared helpers for SpecNative tools.

SpecNative repos have a fixed structure:
  AGENTS.md                 — operating contract
  agents/PRODUCT.md         — user problems / vision
  agents/ARCHITECTURE.md    — system design
  agents/STACK.md           — technology choices
  agents/CONVENTIONS.md     — coding conventions
  agents/COMMANDS.md        — build/run/test commands
  agents/DECISIONS.md       — persistent trade-offs (DEC-XXXX)
  agents/ROADMAP.md         — temporal priorities
  agents/TRACEABILITY.md    — cross-artifact links
  agents/SPEC.md            — default spec (agents domain)
  agents/specs/<initiative>/SPEC.md   — per-initiative specs
  tasks/<initiative>/TASKS.md         — per-initiative tasks
  pipelines/CI.md
  pipelines/CD.md
  .specnative/SCHEMA.md     — TOML schema definition
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
    "pipelines/CI.md",
    "pipelines/CD.md",
    ".specnative/SCHEMA.md",
]

# ── Context document map ──────────────────────────────────────────────────────

CONTEXT_MAP: dict[str, str] = {
    "product":       "agents/PRODUCT.md",
    "architecture":  "agents/ARCHITECTURE.md",
    "stack":         "agents/STACK.md",
    "conventions":   "agents/CONVENTIONS.md",
    "commands":      "agents/COMMANDS.md",
    "decisions":     "agents/DECISIONS.md",
    "roadmap":       "agents/ROADMAP.md",
    "traceability":  "agents/TRACEABILITY.md",
    "agents":        "AGENTS.md",
    "schema":        ".specnative/SCHEMA.md",
    "ci":            "pipelines/CI.md",
    "cd":            "pipelines/CD.md",
    "spec":          "agents/SPEC.md",
}


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
    result: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            result[k] = v
    return result


# ── Spec/Task discovery ───────────────────────────────────────────────────────

def find_specs(root: Path) -> list[Path]:
    """Find all SPEC.md files under root, excluding .specnative."""
    return sorted(
        p for p in root.rglob("SPEC.md")
        if ".specnative" not in p.parts
    )


def find_task_files(root: Path) -> list[Path]:
    """Find all TASKS.md files under tasks/."""
    tasks_dir = root / "tasks"
    if not tasks_dir.is_dir():
        return []
    return sorted(tasks_dir.rglob("TASKS.md"))


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
