from __future__ import annotations

"""
specnative/initiative.py — Workflow engine for SpecNative initiatives.

Manages the full spec-driven lifecycle:
  start      → scaffold SPEC.md with TOML header for a new initiative
  plan       → scaffold TASKS.md derived from a spec's close_criteria
  implement  → show what to implement for a task (reads spec + conventions)
  review     → check implementation against spec acceptance criteria
  close      → mark spec as closed + update TRACEABILITY.md
  decision   → append a new DEC-XXXX entry to DECISIONS.md
  state      → update state field in a SPEC.md or task TOML block

All write operations produce a ForgeResult with the generated/modified content
in data.content so the agent can review before committing to disk.
Use --write to actually write the file.
"""

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.specnative._core import (
    read_file,
    _toml_loads,
    parse_all_toml_blocks,
    find_specs,
    task_state_summary,
    CONTEXT_MAP,
)

TOOL = "specnative.initiative"

_VALID_SPEC_STATES  = ("draft", "review", "approved", "in-progress", "done", "cancelled")
_VALID_TASK_STATES  = ("pending", "in-progress", "done", "blocked", "cancelled")


def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _next_decision_id(decisions_text: str) -> str:
    ids = re.findall(r"DEC-(\d+)", decisions_text)
    if not ids:
        return "DEC-0001"
    return f"DEC-{max(int(i) for i in ids) + 1:04d}"


def _write_or_preview(path: Path, content: str, write: bool) -> dict:
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"written": True, "path": str(path)}
    return {"written": False, "path": str(path), "content": content}


# ── Templates ─────────────────────────────────────────────────────────────────

def _spec_template(initiative: str, problem: str, owner: str) -> str:
    today = _now()
    return f"""\
# Spec: {initiative.replace("-", " ").title()}

```toml
artifact_type = "spec"
id = "SPEC-{initiative.upper()[:20]}"
state = "draft"
owner = "{owner}"
initiative = "{initiative}"
created_at = "{today}"
updated_at = "{today}"
```

## Problem

{problem}

## Goal

<!-- What must be true when this spec is done? -->

## Acceptance Criteria

- [ ] <!-- criterion 1 -->
- [ ] <!-- criterion 2 -->

## Out of Scope

<!-- What is explicitly NOT part of this spec? -->

## Related Decisions

<!-- DEC-XXXX: Short title -->

## Notes

<!-- Any context, constraints, or open questions -->
"""


def _tasks_template(initiative: str, spec_content: str) -> str:
    today = _now()
    # Extract acceptance criteria lines from spec
    criteria = re.findall(r"- \[ \] (.+)", spec_content)
    tasks_blocks = ""
    for i, criterion in enumerate(criteria, 1):
        task_id = f"TASK-{initiative.upper()[:10]}-{i:03d}"
        tasks_blocks += f"""
## {task_id}: {criterion.strip()}

```toml
artifact_type = "task"
id = "{task_id}"
state = "pending"
spec_id = "SPEC-{initiative.upper()[:20]}"
initiative = "{initiative}"
created_at = "{today}"
updated_at = "{today}"
```

**Description:** {criterion.strip()}

**Expected files:**
- [ ] <!-- file or component to create/modify -->

**Validation:**
- [ ] Tests pass
- [ ] Spec criterion met

---
"""

    if not tasks_blocks:
        task_id = f"TASK-{initiative.upper()[:10]}-001"
        tasks_blocks = f"""
## {task_id}: Initial implementation

```toml
artifact_type = "task"
id = "{task_id}"
state = "pending"
spec_id = "SPEC-{initiative.upper()[:20]}"
initiative = "{initiative}"
created_at = "{today}"
updated_at = "{today}"
```

**Description:** Implement the initiative as specified.

**Expected files:**
- [ ] <!-- list files here -->

**Validation:**
- [ ] Tests pass
- [ ] Spec criteria met

---
"""

    return f"# Tasks: {initiative.replace('-', ' ').title()}\n\n" + tasks_blocks.strip() + "\n"


def _decision_block(dec_id: str, title: str, context: str, decision: str, consequences: str, owner: str) -> str:
    today = _now()
    return f"""
## {dec_id}: {title}

```toml
artifact_type = "decision"
id = "{dec_id}"
title = "{title}"
state = "accepted"
owner = "{owner}"
created_at = "{today}"
```

### Context

{context}

### Decision

{decision}

### Consequences

{consequences}

---
"""


# ── Actions ───────────────────────────────────────────────────────────────────

def run(
    *,
    action:       str = "start",
    initiative:   str | None = None,
    problem:      str | None = None,
    task_id:      str | None = None,
    state:        str | None = None,
    # decision fields
    title:        str | None = None,
    context:      str | None = None,
    decision:     str | None = None,
    consequences: str | None = None,
    owner:        str = "team",
    write:        bool = False,
    repo:         str | None = None,
    cwd:          str | None = None,
) -> ForgeResult:
    with Timer() as t:
        root = Path(repo or cwd or ".").resolve()
        if not root.is_dir():
            return ForgeResult.failure(TOOL, [f"Directory not found: {root}"], t.elapsed_ms)

        # ── start ─────────────────────────────────────────────────────────
        if action == "start":
            if not initiative:
                return ForgeResult.failure(TOOL, ["--initiative is required for action=start"], t.elapsed_ms)
            spec_path = root / "agents" / "specs" / initiative / "SPEC.md"
            if spec_path.exists() and not write:
                return ForgeResult.failure(
                    TOOL, [f"Spec already exists: {spec_path.relative_to(root)}"],
                    t.elapsed_ms,
                    suggestion="Use --write to overwrite or choose a different initiative name",
                )
            content = _spec_template(initiative, problem or "<!-- describe the problem here -->", owner)
            result = _write_or_preview(spec_path, content, write)
            return ForgeResult.success(TOOL, {
                "action":     "start",
                "initiative": initiative,
                **result,
            }, t.elapsed_ms)

        # ── plan ──────────────────────────────────────────────────────────
        if action == "plan":
            if not initiative:
                return ForgeResult.failure(TOOL, ["--initiative is required for action=plan"], t.elapsed_ms)
            spec_rel = f"agents/specs/{initiative}/SPEC.md"
            spec_content = read_file(root, spec_rel) or read_file(root, "agents/SPEC.md") or ""
            tasks_path = root / "tasks" / initiative / "TASKS.md"
            content = _tasks_template(initiative, spec_content)
            result = _write_or_preview(tasks_path, content, write)
            return ForgeResult.success(TOOL, {
                "action":        "plan",
                "initiative":    initiative,
                "spec_used":     spec_rel,
                "criteria_found": len(re.findall(r"- \[ \] (.+)", spec_content)),
                **result,
            }, t.elapsed_ms)

        # ── implement ─────────────────────────────────────────────────────
        if action == "implement":
            if not initiative:
                return ForgeResult.failure(TOOL, ["--initiative is required"], t.elapsed_ms)

            spec_content     = read_file(root, f"agents/specs/{initiative}/SPEC.md") or read_file(root, "agents/SPEC.md") or ""
            conventions      = read_file(root, "agents/CONVENTIONS.md") or ""
            commands         = read_file(root, "agents/COMMANDS.md") or ""
            architecture     = read_file(root, "agents/ARCHITECTURE.md") or ""
            stack            = read_file(root, "agents/STACK.md") or ""

            tasks_rel = f"tasks/{initiative}/TASKS.md"
            tasks_content = read_file(root, tasks_rel) or ""
            all_tasks = parse_all_toml_blocks(tasks_content)

            # Filter to specific task if provided
            if task_id:
                target_tasks = [t for t in all_tasks if t.get("id") == task_id]
            else:
                target_tasks = [t for t in all_tasks if t.get("state") in ("pending", "in-progress")]

            return ForgeResult.success(TOOL, {
                "action":       "implement",
                "initiative":   initiative,
                "task_id":      task_id,
                "target_tasks": target_tasks,
                "spec_summary": spec_content[:2000],
                "conventions":  conventions[:1500],
                "commands":     commands[:500],
                "architecture": architecture[:1000],
                "stack":        stack[:500],
                "hint":         (
                    "Read spec + conventions before coding. "
                    "Each task has expected_files. "
                    "Update task state to 'in-progress' before starting, 'done' when complete."
                ),
            }, t.elapsed_ms)

        # ── review ────────────────────────────────────────────────────────
        if action == "review":
            if not initiative:
                return ForgeResult.failure(TOOL, ["--initiative is required"], t.elapsed_ms)

            spec_content  = read_file(root, f"agents/specs/{initiative}/SPEC.md") or read_file(root, "agents/SPEC.md") or ""
            tasks_content = read_file(root, f"tasks/{initiative}/TASKS.md") or ""
            all_tasks     = parse_all_toml_blocks(tasks_content)

            spec_meta   = _toml_loads(spec_content)
            criteria    = re.findall(r"- \[ \] (.+)", spec_content)
            done_tasks  = [t for t in all_tasks if t.get("state") == "done"]
            total_tasks = len(all_tasks)

            review_result = {
                "action":          "review",
                "initiative":      initiative,
                "spec_state":      spec_meta.get("state"),
                "criteria_count":  len(criteria),
                "criteria":        criteria,
                "tasks_total":     total_tasks,
                "tasks_done":      len(done_tasks),
                "tasks_pending":   sum(1 for t in all_tasks if t.get("state") == "pending"),
                "tasks_blocked":   sum(1 for t in all_tasks if t.get("state") == "blocked"),
                "ready_to_close":  len(done_tasks) == total_tasks and total_tasks > 0,
            }
            ok = review_result["ready_to_close"]
            suggestion = None if ok else f"{total_tasks - len(done_tasks)} task(s) not yet done"

            return ForgeResult(
                ok=ok,
                tool=TOOL,
                data=review_result,
                errors=[] if ok else ["Initiative not ready to close"],
                suggestion=suggestion,
                duration_ms=t.elapsed_ms,
            )

        # ── close ─────────────────────────────────────────────────────────
        if action == "close":
            if not initiative:
                return ForgeResult.failure(TOOL, ["--initiative is required"], t.elapsed_ms)

            spec_rel     = f"agents/specs/{initiative}/SPEC.md"
            spec_path    = root / spec_rel
            spec_content = read_file(root, spec_rel)
            if spec_content is None:
                return ForgeResult.failure(TOOL, [f"Spec not found: {spec_rel}"], t.elapsed_ms)

            today = _now()
            # Update state + updated_at in the TOML block
            updated = re.sub(r'(state\s*=\s*")[^"]*(")', r'\1done\2', spec_content)
            updated = re.sub(r'(updated_at\s*=\s*")[^"]*(")', rf'\1{today}\2', updated)

            # Append traceability entry
            trace_path    = root / "agents" / "TRACEABILITY.md"
            trace_content = read_file(root, "agents/TRACEABILITY.md") or "# Traceability\n\n"
            spec_meta     = _toml_loads(spec_content)
            trace_entry   = f"\n| {spec_meta.get('id', initiative)} | {spec_rel} | closed | {today} |\n"
            updated_trace = trace_content.rstrip() + trace_entry

            results = []
            results.append(_write_or_preview(spec_path, updated, write))
            results.append(_write_or_preview(trace_path, updated_trace, write))

            return ForgeResult.success(TOOL, {
                "action":     "close",
                "initiative": initiative,
                "spec_path":  spec_rel,
                "written":    write,
                "spec_preview":  updated if not write else None,
                "trace_preview": updated_trace if not write else None,
            }, t.elapsed_ms)

        # ── decision ──────────────────────────────────────────────────────
        if action == "decision":
            if not title or not context or not decision or not consequences:
                return ForgeResult.failure(
                    TOOL,
                    ["--title, --context, --decision, --consequences are all required for action=decision"],
                    t.elapsed_ms,
                )
            dec_path    = root / "agents" / "DECISIONS.md"
            existing    = read_file(root, "agents/DECISIONS.md") or "# Decisions\n\n"
            dec_id      = _next_decision_id(existing)
            new_block   = _decision_block(dec_id, title, context, decision, consequences, owner)
            updated     = existing.rstrip() + "\n" + new_block
            result      = _write_or_preview(dec_path, updated, write)

            return ForgeResult.success(TOOL, {
                "action":     "decision",
                "id":         dec_id,
                "title":      title,
                **result,
            }, t.elapsed_ms)

        # ── state ─────────────────────────────────────────────────────────
        if action == "state":
            if not initiative or not state:
                return ForgeResult.failure(TOOL, ["--initiative and --state are required for action=state"], t.elapsed_ms)

            if task_id:
                # Update task state in TASKS.md
                tasks_rel  = f"tasks/{initiative}/TASKS.md"
                tasks_path = root / tasks_rel
                content    = read_file(root, tasks_rel)
                if content is None:
                    return ForgeResult.failure(TOOL, [f"Tasks file not found: {tasks_rel}"], t.elapsed_ms)
                if task_id not in content:
                    return ForgeResult.failure(TOOL, [f"Task ID '{task_id}' not found in {tasks_rel}"], t.elapsed_ms)
                today   = _now()
                # Replace state only within the block that contains task_id
                # Strategy: find the block, replace state + updated_at
                updated = _update_state_in_block(content, task_id, state, today)
                result  = _write_or_preview(tasks_path, updated, write)
                return ForgeResult.success(TOOL, {
                    "action": "state", "task_id": task_id, "new_state": state, **result
                }, t.elapsed_ms)
            else:
                # Update spec state
                spec_rel  = f"agents/specs/{initiative}/SPEC.md"
                spec_path = root / spec_rel
                content   = read_file(root, spec_rel)
                if content is None:
                    return ForgeResult.failure(TOOL, [f"Spec not found: {spec_rel}"], t.elapsed_ms)
                today   = _now()
                updated = re.sub(r'(state\s*=\s*")[^"]*(")', rf'\1{state}\2', content)
                updated = re.sub(r'(updated_at\s*=\s*")[^"]*(")', rf'\1{today}\2', updated)
                result  = _write_or_preview(spec_path, updated, write)
                return ForgeResult.success(TOOL, {
                    "action": "state", "initiative": initiative, "new_state": state, **result
                }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: start | plan | implement | review | close | decision | state"],
            t.elapsed_ms,
        )


def _update_state_in_block(content: str, task_id: str, new_state: str, today: str) -> str:
    """Update state + updated_at inside the TOML block that contains task_id."""
    lines   = content.splitlines(keepends=True)
    result  = []
    in_block = False
    found_id = False

    for line in lines:
        if line.strip() == "```toml":
            in_block = True
            block_lines: list[str] = [line]
            continue
        if in_block:
            if line.strip() == "```":
                in_block = False
                if found_id:
                    found_id = False
                    block_str = "".join(block_lines)
                    block_str = re.sub(r'(state\s*=\s*")[^"]*(")', rf'\1{new_state}\2', block_str)
                    block_str = re.sub(r'(updated_at\s*=\s*")[^"]*(")', rf'\1{today}\2', block_str)
                    result.append(block_str)
                    result.append(line)
                else:
                    result.extend(block_lines)
                    result.append(line)
                block_lines = []
                continue
            block_lines.append(line)
            if f'id = "{task_id}"' in line or f"id = '{task_id}'" in line:
                found_id = True
        else:
            result.append(line)

    return "".join(result)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="start",
                   choices=["start", "plan", "implement", "review", "close", "decision", "state"])
    p.add_argument("--initiative",   default=None, help="Initiative folder name")
    p.add_argument("--problem",      default=None, help="Problem description for action=start")
    p.add_argument("--task-id",      default=None, dest="task_id", help="Task ID for action=implement/state")
    p.add_argument("--state",        default=None, help=f"New state. Spec: {_VALID_SPEC_STATES} | Task: {_VALID_TASK_STATES}")
    p.add_argument("--title",        default=None, help="Decision title for action=decision")
    p.add_argument("--context",      default=None, help="Decision context")
    p.add_argument("--decision",     default=None, help="The decision made")
    p.add_argument("--consequences", default=None, help="Consequences of the decision")
    p.add_argument("--owner",        default="team")
    p.add_argument("--write",        action="store_true", help="Actually write files (default: preview only)")
    p.add_argument("--repo",         default=None)
    p.add_argument("--cwd",          default=None)


if __name__ == "__main__":
    make_cli(TOOL, "SpecNative initiative lifecycle: start→plan→implement→review→close", run, _add_args)
