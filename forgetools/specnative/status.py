from __future__ import annotations

"""
specnative/status.py — Observe the health and state of a SpecNative repository.

Actions:
    status      — all specs with their states + task state counts per spec
    validate    — verify all required SpecNative files exist + TOML parseable
    list-specs  — table of specs: id, state, owner, initiative
    export      — full metadata index (specs + task files) as structured JSON
"""

import argparse
import json
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.specnative._core import (
    REQUIRED_FILES,
    find_specs,
    find_task_files,
    parse_spec,
    task_state_summary,
    read_file,
    parse_all_toml_blocks,
)

TOOL = "specnative.status"


def run(
    *,
    action: str = "status",
    repo:   str | None = None,
    cwd:    str | None = None,
) -> ForgeResult:
    with Timer() as t:
        root = Path(repo or cwd or ".").resolve()
        if not root.is_dir():
            return ForgeResult.failure(TOOL, [f"Directory not found: {root}"], t.elapsed_ms)

        # ── validate ──────────────────────────────────────────────────────
        if action == "validate":
            missing = [f for f in REQUIRED_FILES if not (root / f).is_file()]
            present = [f for f in REQUIRED_FILES if (root / f).is_file()]

            # Check TOML parseability for specs and task files
            toml_errors: list[str] = []
            for spec_path in find_specs(root):
                text = spec_path.read_text(encoding="utf-8")
                if "```toml" not in text:
                    toml_errors.append(f"{spec_path.relative_to(root)}: no TOML block")

            ok = not missing and not toml_errors
            return ForgeResult(
                ok=ok,
                tool=TOOL,
                data={
                    "valid":         ok,
                    "present_count": len(present),
                    "missing_count": len(missing),
                    "missing":       missing,
                    "present":       present,
                    "toml_errors":   toml_errors,
                },
                errors=[] if ok else [f"{len(missing)} required file(s) missing"] + toml_errors[:5],
                suggestion=None if ok else "Run `python3 install.py` to scaffold missing files",
                duration_ms=t.elapsed_ms,
            )

        # ── status ────────────────────────────────────────────────────────
        if action == "status":
            spec_files = find_specs(root)
            task_files = find_task_files(root)

            # Build task summary keyed by initiative
            task_summaries: dict[str, dict[str, int]] = {}
            for tf in task_files:
                # tasks/<initiative>/TASKS.md → initiative = parent dir name
                initiative = tf.parent.name
                task_summaries[initiative] = task_state_summary(tf)

            specs_summary = []
            for sp in spec_files:
                meta = parse_spec(sp, root)
                initiative = meta.get("initiative") or sp.parent.name
                specs_summary.append({
                    "id":         meta.get("id"),
                    "state":      meta.get("state"),
                    "owner":      meta.get("owner"),
                    "initiative": initiative,
                    "path":       meta["_path"],
                    "tasks":      task_summaries.get(initiative, {}),
                })

            state_counts: dict[str, int] = {}
            for s in specs_summary:
                st = s.get("state") or "unknown"
                state_counts[st] = state_counts.get(st, 0) + 1

            return ForgeResult.success(TOOL, {
                "root":         str(root),
                "spec_count":   len(spec_files),
                "task_files":   len(task_files),
                "states":       state_counts,
                "specs":        specs_summary,
            }, t.elapsed_ms)

        # ── list-specs ────────────────────────────────────────────────────
        if action == "list-specs":
            spec_files = find_specs(root)
            specs = []
            for sp in spec_files:
                meta = parse_spec(sp, root)
                specs.append({
                    "id":         meta.get("id"),
                    "state":      meta.get("state"),
                    "owner":      meta.get("owner"),
                    "initiative": meta.get("initiative") or sp.parent.name,
                    "created_at": meta.get("created_at"),
                    "updated_at": meta.get("updated_at"),
                    "path":       meta["_path"],
                })
            return ForgeResult.success(TOOL, {
                "count": len(specs),
                "specs": specs,
            }, t.elapsed_ms)

        # ── export ────────────────────────────────────────────────────────
        if action == "export":
            spec_files  = find_specs(root)
            task_files  = find_task_files(root)

            specs_data = [parse_spec(sp, root) for sp in spec_files]

            tasks_data = []
            for tf in task_files:
                text  = tf.read_text(encoding="utf-8")
                tasks = parse_all_toml_blocks(text)
                tasks_data.append({
                    "_path":      str(tf.relative_to(root)),
                    "initiative": tf.parent.name,
                    "tasks":      tasks,
                    "count":      len(tasks),
                })

            return ForgeResult.success(TOOL, {
                "root":       str(root),
                "spec_count": len(specs_data),
                "task_files": len(tasks_data),
                "specs":      specs_data,
                "task_files_data": tasks_data,
            }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: status | validate | list-specs | export"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="status",
                   choices=["status", "validate", "list-specs", "export"])
    p.add_argument("--repo", default=None,
                   help="SpecNative repository root (default: cwd)")
    p.add_argument("--cwd", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "SpecNative repository health and spec state overview", run, _add_args)
