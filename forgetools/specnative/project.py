from __future__ import annotations

"""SpecNative project definition, health, and guided document updates."""

import argparse
import re
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.specnative._core import (
    context_map_for,
    context_rel,
    find_specs,
    read_file,
    required_files_for,
    spec_path_for,
    tasks_path_for,
)

TOOL = "specnative.project"

PLACEHOLDER_RE = re.compile(
    r"<!--|^#\s+Template|Tu nombre\b|tu proyecto\b|descripcion del proyecto\b|Describe\b.*\baqui\b",
    re.IGNORECASE | re.MULTILINE,
)

CORE_DOCS = ("product", "architecture", "stack", "conventions", "commands", "decisions", "roadmap")

TEMPLATES: dict[str, str] = {
    "product": """# PRODUCT.md

Fuente de verdad del producto.

## Problema

## Usuarios

## Objetivos

## No objetivos

## Valor diferencial
""",
    "architecture": """# ARCHITECTURE.md

## Modulos principales

## Limites y reglas

## Flujo de datos principal

## Restricciones arquitectonicas
""",
    "stack": """# STACK.md

## Lenguajes y runtimes

## Frameworks y librerias clave

## Infraestructura

## Restricciones

## Herramientas de desarrollo
""",
    "conventions": """# CONVENTIONS.md

## Naming

## Estructura de carpetas

## Estilo y formato

## Testing

## Commits y PRs
""",
    "commands": """# COMMANDS.md

## Setup

## Desarrollo

## Tests

## Lint y formato

## Build
""",
    "decisions": """# DECISIONS.md

Registro de decisiones persistentes que las iniciativas futuras deben respetar.

### DEC-0001 - Titulo de la decision

- Fecha: YYYY-MM-DD
- Estado: `proposed | accepted | deprecated | replaced`
- Contexto:
- Decision:
- Consecuencias:
- Reemplaza: none
""",
    "roadmap": """# ROADMAP.md

## Ahora

## Despues

## Mas adelante

## No por ahora
""",
    "traceability": """# TRACEABILITY.md

Vinculos entre specs, tareas, decisiones y evidencia de validacion.

### NOMBRE-INICIATIVA - SPEC-XXXX

- Spec:
- Tasks:
- Decisions:
- Artifacts:
- Validation:
""",
    "spec": """# SPEC.md

```toml
artifact_type = "spec"
id = "SPEC-XXXX"
state = "draft"
owner = ""
created_at = "YYYY-MM-DD"
updated_at = "YYYY-MM-DD"
replaces = "none"
related_tasks = []
related_decisions = []
artifacts = []
validation = []
```

## Resumen

## Problema

## Objetivo

## Alcance

## Requisitos funcionales

## Requisitos no funcionales

## Criterios de aceptacion

## Dependencias y riesgos

## Plan de validacion
""",
    "tasks": """# TASKS.md

```toml
artifact_type = "task_file"
initiative = ""
spec_id = "SPEC-XXXX"
owner = ""
state = "todo"
```

## Tareas

### TASK-0001 - Titulo

```toml
id = "TASK-0001"
title = ""
state = "todo"
owner = ""
dependencies = []
expected_files = []
close_criteria = ""
validation = []
```
""",
    "session": """+++
[session]
state = "idle"
agent = ""
initiative = ""
task = ""
intent = ""
last_updated = ""
+++

# Active Session

## Current state

## Next steps

## Context for next agent
""",
}


def _has_real_content(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < 80:
        return False
    real_lines = [line for line in text.splitlines() if line.strip() and not PLACEHOLDER_RE.search(line)]
    return len(real_lines) >= 5


def _doc_path(root: Path, document: str) -> Path | None:
    rel = context_rel(root, document)
    return None if rel is None else root / rel


def _write_or_preview(path: Path, content: str, write: bool) -> dict:
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return {
        "written": write,
        "path": str(path),
        "content": None if write else content.rstrip() + "\n",
    }


def _health(root: Path) -> dict:
    required = required_files_for(root)
    missing_required = [rel for rel in required if not (root / rel).exists()]
    docs = []
    for doc in CORE_DOCS:
        path = _doc_path(root, doc)
        exists = bool(path and path.exists())
        real_content = bool(path and _has_real_content(path))
        docs.append({
            "document": doc,
            "path": None if path is None else str(path.relative_to(root)),
            "exists": exists,
            "has_real_content": real_content,
            "state": "ok" if real_content else "missing" if not exists else "empty_or_placeholder",
        })

    specs_without_tasks = []
    for spec_file in find_specs(root):
        if "spec-native" not in spec_file.parts and "agents" not in spec_file.parts:
            continue
        initiative = spec_file.parent.name
        if initiative in ("spec-native", "agents", "specs"):
            continue
        if not tasks_path_for(root, initiative).exists():
            specs_without_tasks.append(str(spec_file.relative_to(root)))

    issues = []
    issues.extend({"type": "missing_required", "path": rel} for rel in missing_required)
    issues.extend({"type": "doc_gap", **doc} for doc in docs if doc["state"] != "ok")
    issues.extend({"type": "spec_without_tasks", "path": rel} for rel in specs_without_tasks)

    return {
        "root": str(root),
        "layout": "spec-native" if (root / "spec-native").is_dir() else "legacy-agents",
        "score": len([doc for doc in docs if doc["state"] == "ok"]),
        "total_core_docs": len(docs),
        "missing_required": missing_required,
        "core_docs": docs,
        "specs_without_tasks": specs_without_tasks,
        "issues": issues,
        "healthy": not issues,
    }


def _replace_section(text: str, heading: str, content: str) -> tuple[str, bool]:
    pattern = re.compile(
        r"(^##+\s+" + re.escape(heading).strip() + r"\s*$\n)(.*?)(?=^##+\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    replacement = lambda match: match.group(1) + "\n" + content.rstrip() + "\n\n"
    updated, count = pattern.subn(replacement, text, count=1)
    if count:
        return updated.rstrip() + "\n", True
    return text.rstrip() + f"\n\n## {heading}\n\n{content.rstrip()}\n", False


def run(
    *,
    action: str = "health-check",
    document: str | None = None,
    section: str | None = None,
    what_changed: str = "",
    content: str | None = None,
    initiative: str | None = None,
    write: bool = False,
    repo: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        root = Path(repo or cwd or ".").resolve()
        if not root.is_dir():
            return ForgeResult.failure(TOOL, [f"Directory not found: {root}"], t.elapsed_ms)

        if action == "health-check":
            return ForgeResult.success(TOOL, _health(root), t.elapsed_ms)

        if action == "suggest-next":
            health = _health(root)
            suggestions = []
            gaps = [doc for doc in health["core_docs"] if doc["state"] != "ok"]
            if gaps:
                suggestions.append({
                    "priority": 1,
                    "action": "fill_project_context",
                    "why": "Core SpecNative documents are missing or placeholder-only",
                    "documents": [doc["document"] for doc in gaps[:5]],
                })
            session_path = _doc_path(root, "session")
            if session_path and session_path.exists() and "in_progress" in session_path.read_text(encoding="utf-8"):
                suggestions.append({
                    "priority": 1,
                    "action": "resume_session",
                    "why": "SESSION.md indicates active work",
                    "command": "specnative session --action resume",
                })
            for rel in health["specs_without_tasks"][:3]:
                suggestions.append({
                    "priority": 2,
                    "action": "plan_tasks",
                    "why": "Spec exists without linked TASKS.md",
                    "spec": rel,
                })
            if not suggestions:
                suggestions.append({
                    "priority": 3,
                    "action": "review_and_evolve",
                    "why": "SpecNative structure is healthy",
                    "commands": ["specnative status --action status", "specnative project --action health-check"],
                })
            return ForgeResult.success(TOOL, {"suggestions": suggestions[:3], "health": health}, t.elapsed_ms)

        if action == "snapshot":
            docs = ["product", "architecture", "stack", "decisions", "roadmap", "session"]
            snapshot = {}
            for doc in docs:
                rel = context_rel(root, doc)
                snapshot[doc] = {"path": rel, "content": read_file(root, rel) if rel else None}
            if initiative:
                sp = spec_path_for(root, initiative)
                tp = tasks_path_for(root, initiative)
                snapshot["spec"] = {"path": str(sp.relative_to(root)), "content": sp.read_text(encoding="utf-8") if sp.exists() else None}
                snapshot["tasks"] = {"path": str(tp.relative_to(root)), "content": tp.read_text(encoding="utf-8") if tp.exists() else None}
            return ForgeResult.success(TOOL, {"root": str(root), "snapshot": snapshot}, t.elapsed_ms)

        if action == "read-template":
            if not document:
                return ForgeResult.failure(TOOL, ["--document is required"], t.elapsed_ms)
            template = TEMPLATES.get(document.lower())
            if template is None:
                return ForgeResult.failure(TOOL, [f"Unknown template '{document}'"], t.elapsed_ms, suggestion=f"Valid: {', '.join(sorted(TEMPLATES))}")
            return ForgeResult.success(TOOL, {"document": document, "template": template}, t.elapsed_ms)

        if action == "refine-document":
            if not document or content is None:
                return ForgeResult.failure(TOOL, ["--document and --content are required"], t.elapsed_ms)
            path = _doc_path(root, document)
            if path is None:
                return ForgeResult.failure(TOOL, [f"Unknown document '{document}'"], t.elapsed_ms, suggestion=f"Valid: {', '.join(sorted(context_map_for(root)))}")
            result = _write_or_preview(path, content, write)
            return ForgeResult.success(TOOL, {
                "action": action,
                "document": document,
                "what_changed": what_changed,
                **result,
            }, t.elapsed_ms)

        if action == "update-section":
            if not document or not section or content is None:
                return ForgeResult.failure(TOOL, ["--document, --section and --content are required"], t.elapsed_ms)
            path = _doc_path(root, document)
            if path is None:
                return ForgeResult.failure(TOOL, [f"Unknown document '{document}'"], t.elapsed_ms)
            existing = path.read_text(encoding="utf-8") if path.exists() else TEMPLATES.get(document, f"# {path.name}\n")
            updated, replaced = _replace_section(existing, section, content)
            result = _write_or_preview(path, updated, write)
            return ForgeResult.success(TOOL, {
                "action": action,
                "document": document,
                "section": section,
                "replaced_existing_section": replaced,
                **result,
            }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: health-check | suggest-next | snapshot | read-template | refine-document | update-section"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="health-check", choices=[
        "health-check", "suggest-next", "snapshot", "read-template", "refine-document", "update-section",
    ])
    p.add_argument("--document", default=None)
    p.add_argument("--section", default=None)
    p.add_argument("--what-changed", default="")
    p.add_argument("--content", default=None)
    p.add_argument("--initiative", default=None)
    p.add_argument("--write", action="store_true")
    p.add_argument("--repo", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "SpecNative project health and guided document updates", run, _add_args)
