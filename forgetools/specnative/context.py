from __future__ import annotations

"""
specnative/context.py — Read SpecNative context documents and specs.

Actions:
    read        — read any context document by short name
                  names: product | architecture | stack | conventions |
                         commands | decisions | roadmap | traceability |
                         agents | schema | ci | cd | spec
    read-spec   — read a spec file by initiative name (empty = agents/SPEC.md)
    list-tasks  — all tasks for a given initiative from tasks/<initiative>/TASKS.md
    read-tasks  — raw content of tasks/<initiative>/TASKS.md
    decisions   — parsed list of all decisions (DEC-XXXX) from DECISIONS.md
    traceability — parsed cross-artifact links from TRACEABILITY.md
"""

import argparse
import re
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.specnative._core import (
    CONTEXT_MAP,
    read_file,
    parse_all_toml_blocks,
    _toml_loads,
)

TOOL = "specnative.context"


def _parse_decisions(text: str) -> list[dict]:
    """Extract DEC-XXXX entries from DECISIONS.md."""
    decisions = []
    # Look for TOML blocks (SpecNative format)
    blocks = parse_all_toml_blocks(text)
    if blocks:
        return blocks

    # Fallback: parse markdown headers like ## DEC-0001: Title
    for m in re.finditer(r"##\s+(DEC-\d+)[:\s]+(.+)", text):
        dec_id = m.group(1)
        title  = m.group(2).strip()
        decisions.append({"id": dec_id, "title": title})
    return decisions


def _parse_traceability(text: str) -> list[dict]:
    """Extract traceability entries (TOML blocks or table rows)."""
    blocks = parse_all_toml_blocks(text)
    if blocks:
        return blocks
    # Fallback: parse markdown table rows
    entries = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) >= 3 and not set(cells[0]) <= {"-", " "}:
            entries.append({"artifact": cells[0], "spec": cells[1] if len(cells) > 1 else "", "status": cells[2] if len(cells) > 2 else ""})
    return entries


def run(
    *,
    action:     str = "read",
    document:   str | None = None,
    initiative: str | None = None,
    repo:       str | None = None,
    cwd:        str | None = None,
) -> ForgeResult:
    with Timer() as t:
        root = Path(repo or cwd or ".").resolve()
        if not root.is_dir():
            return ForgeResult.failure(TOOL, [f"Directory not found: {root}"], t.elapsed_ms)

        # ── read ──────────────────────────────────────────────────────────
        if action == "read":
            if not document:
                return ForgeResult.failure(
                    TOOL,
                    ["--document is required. Options: " + " | ".join(CONTEXT_MAP)],
                    t.elapsed_ms,
                )
            rel = CONTEXT_MAP.get(document)
            if rel is None:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unknown document '{document}'. Valid: {', '.join(CONTEXT_MAP)}"],
                    t.elapsed_ms,
                )
            content = read_file(root, rel)
            if content is None:
                return ForgeResult.failure(
                    TOOL,
                    [f"File not found: {rel}"],
                    t.elapsed_ms,
                    suggestion="Run `python3 install.py` to scaffold the SpecNative structure",
                )
            return ForgeResult.success(TOOL, {
                "document": document,
                "path":     rel,
                "size":     len(content),
                "content":  content,
            }, t.elapsed_ms)

        # ── read-spec ─────────────────────────────────────────────────────
        if action == "read-spec":
            if initiative:
                rel = f"agents/specs/{initiative}/SPEC.md"
            else:
                rel = "agents/SPEC.md"
            content = read_file(root, rel)
            if content is None:
                return ForgeResult.failure(
                    TOOL,
                    [f"Spec not found: {rel}"],
                    t.elapsed_ms,
                    suggestion=f"Create it with: specnative initiative --action start --initiative {initiative or 'name'}",
                )
            meta = _toml_loads(content)
            return ForgeResult.success(TOOL, {
                "initiative": initiative or "(default)",
                "path":       rel,
                "metadata":   meta,
                "content":    content,
            }, t.elapsed_ms)

        # ── list-tasks ────────────────────────────────────────────────────
        if action == "list-tasks":
            if not initiative:
                return ForgeResult.failure(TOOL, ["--initiative is required for action=list-tasks"], t.elapsed_ms)
            rel = f"tasks/{initiative}/TASKS.md"
            content = read_file(root, rel)
            if content is None:
                return ForgeResult.failure(TOOL, [f"Tasks file not found: {rel}"], t.elapsed_ms)
            tasks = parse_all_toml_blocks(content)
            # Count states
            state_counts: dict[str, int] = {}
            for task in tasks:
                st = task.get("state", "unknown")
                state_counts[st] = state_counts.get(st, 0) + 1
            return ForgeResult.success(TOOL, {
                "initiative": initiative,
                "path":       rel,
                "count":      len(tasks),
                "states":     state_counts,
                "tasks":      tasks,
            }, t.elapsed_ms)

        # ── read-tasks ────────────────────────────────────────────────────
        if action == "read-tasks":
            if not initiative:
                return ForgeResult.failure(TOOL, ["--initiative is required for action=read-tasks"], t.elapsed_ms)
            rel = f"tasks/{initiative}/TASKS.md"
            content = read_file(root, rel)
            if content is None:
                return ForgeResult.failure(TOOL, [f"Tasks file not found: {rel}"], t.elapsed_ms)
            return ForgeResult.success(TOOL, {
                "initiative": initiative,
                "path":       rel,
                "size":       len(content),
                "content":    content,
            }, t.elapsed_ms)

        # ── decisions ─────────────────────────────────────────────────────
        if action == "decisions":
            content = read_file(root, "agents/DECISIONS.md")
            if content is None:
                return ForgeResult.failure(TOOL, ["agents/DECISIONS.md not found"], t.elapsed_ms)
            entries = _parse_decisions(content)
            return ForgeResult.success(TOOL, {
                "path":    "agents/DECISIONS.md",
                "count":   len(entries),
                "decisions": entries,
            }, t.elapsed_ms)

        # ── traceability ──────────────────────────────────────────────────
        if action == "traceability":
            content = read_file(root, "agents/TRACEABILITY.md")
            if content is None:
                return ForgeResult.failure(TOOL, ["agents/TRACEABILITY.md not found"], t.elapsed_ms)
            entries = _parse_traceability(content)
            return ForgeResult.success(TOOL, {
                "path":    "agents/TRACEABILITY.md",
                "count":   len(entries),
                "entries": entries,
            }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: read | read-spec | list-tasks | read-tasks | decisions | traceability"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="read",
                   choices=["read", "read-spec", "list-tasks", "read-tasks", "decisions", "traceability"])
    p.add_argument("--document",   default=None,
                   help=f"Context document name: {' | '.join(CONTEXT_MAP)}")
    p.add_argument("--initiative", default=None,
                   help="Initiative folder name (e.g. authentication)")
    p.add_argument("--repo",       default=None)
    p.add_argument("--cwd",        default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Read SpecNative context documents, specs, and tasks", run, _add_args)
