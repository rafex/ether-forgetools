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
    task_state_summary,
    CONTEXT_MAP,
    context_rel,
    spec_path_for,
    tasks_path_for,
    workflows_dir,
    SPEC_STATES,
    TASK_STATES,
    DECISION_STATES,
    AGENT_WORKFLOW_SEQUENCE,
    PLACEMENT_DECISION_TREE,
)

TOOL = "specnative.initiative"

_VALID_SPEC_STATES     = SPEC_STATES      # draft | active | blocked | done | superseded
_VALID_TASK_STATES     = TASK_STATES      # todo | in_progress | blocked | done
_VALID_DECISION_STATES = DECISION_STATES  # proposed | accepted | deprecated | replaced


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
    spec_id = f"SPEC-{initiative.upper()[:20]}"
    return f"""\
# Spec: {initiative.replace("-", " ").title()}

```toml
artifact_type = "spec"
id = "{spec_id}"
state = "draft"
owner = "{owner}"
initiative = "{initiative}"
created_at = "{today}"
updated_at = "{today}"
related_tasks = []
related_decisions = []
artifacts = []
validation = []
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

## Risks

<!-- Identified risks and mitigations -->

## Notes

<!-- Any context, constraints, or open questions -->
"""


def _tasks_template(initiative: str, spec_content: str) -> str:
    today = _now()
    spec_id = f"SPEC-{initiative.upper()[:20]}"
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
state = "todo"
owner = "team"
spec_id = "{spec_id}"
initiative = "{initiative}"
dependencies = []
expected_files = []
close_criteria = "{criterion.strip()}"
validation = []
created_at = "{today}"
updated_at = "{today}"
```

**Description:** {criterion.strip()}

**Expected files:**
- [ ] <!-- file or component to create/modify -->

**Validation:**
- [ ] Tests pass
- [ ] Spec criterion met: `{criterion.strip()}`

---
"""

    if not tasks_blocks:
        task_id = f"TASK-{initiative.upper()[:10]}-001"
        tasks_blocks = f"""
## {task_id}: Initial implementation

```toml
artifact_type = "task"
id = "{task_id}"
state = "todo"
owner = "team"
spec_id = "{spec_id}"
initiative = "{initiative}"
dependencies = []
expected_files = []
close_criteria = "Implement the initiative as specified and all tests pass"
validation = []
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


def _decision_block(dec_id: str, title: str, context: str, decision: str,
                    consequences: str, owner: str, state: str = "proposed") -> str:
    today = _now()
    return f"""
## {dec_id}: {title}

```toml
artifact_type = "decision"
id = "{dec_id}"
title = "{title}"
state = "{state}"
owner = "{owner}"
created_at = "{today}"
updated_at = "{today}"
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
    action:          str = "start",
    initiative:      str | None = None,
    problem:         str | None = None,
    task_id:         str | None = None,
    state:           str | None = None,
    # decision fields
    title:           str | None = None,
    context:         str | None = None,
    decision:        str | None = None,
    consequences:    str | None = None,
    decision_state:  str = "proposed",   # proposed → accepted | deprecated | replaced
    owner:           str = "team",
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
            spec_path = spec_path_for(root, initiative)
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
            spec_path = spec_path_for(root, initiative)
            spec_rel = str(spec_path.relative_to(root))
            default_spec_rel = str(spec_path_for(root, None).relative_to(root))
            spec_content = read_file(root, spec_rel) or read_file(root, default_spec_rel) or ""
            tasks_path = tasks_path_for(root, initiative)
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

            # Official 9-step agent workflow — load minimum necessary context
            # Step 1-4: context loading
            roadmap       = read_file(root, context_rel(root, "roadmap") or "agents/ROADMAP.md") or ""
            product       = read_file(root, context_rel(root, "product") or "agents/PRODUCT.md") or ""
            decisions     = read_file(root, context_rel(root, "decisions") or "agents/DECISIONS.md") or ""
            architecture  = read_file(root, context_rel(root, "architecture") or "agents/ARCHITECTURE.md") or ""
            # Step 5: spec
            spec_rel      = str(spec_path_for(root, initiative).relative_to(root))
            default_spec  = str(spec_path_for(root, None).relative_to(root))
            spec_content  = (read_file(root, spec_rel) or read_file(root, default_spec) or "")
            # Step 7: workflow guide
            impl_workflow = read_file(root, str((workflows_dir(root) / "IMPLEMENTATION.md").relative_to(root))) or ""
            # Supporting context
            conventions   = read_file(root, context_rel(root, "conventions") or "agents/CONVENTIONS.md") or ""
            commands      = read_file(root, context_rel(root, "commands") or "agents/COMMANDS.md") or ""
            stack         = read_file(root, context_rel(root, "stack") or "agents/STACK.md") or ""

            # Step 6: tasks
            tasks_rel     = str(tasks_path_for(root, initiative).relative_to(root))
            tasks_content = read_file(root, tasks_rel) or ""
            all_tasks     = [task for task in parse_all_toml_blocks(tasks_content) if task.get("id")]

            # Filter to specific task if provided; default to todo/in_progress
            if task_id:
                target_tasks = [t for t in all_tasks if t.get("id") == task_id]
            else:
                target_tasks = [t for t in all_tasks if t.get("state") in ("todo", "in_progress")]

            return ForgeResult.success(TOOL, {
                "action":           "implement",
                "initiative":       initiative,
                "task_id":          task_id,
                "target_tasks":     target_tasks,
                "spec_summary":     spec_content[:2000],
                "conventions":      conventions[:1500],
                "commands":         commands[:500],
                "architecture":     architecture[:1000],
                "stack":            stack[:500],
                "roadmap_summary":  roadmap[:500],
                "decisions_hint":   decisions[:800],
                "impl_workflow":    impl_workflow[:1000],
                "agent_sequence":   AGENT_WORKFLOW_SEQUENCE,
                "placement_test":   [f"{q} → {doc}" for q, doc in PLACEMENT_DECISION_TREE],
                "hint": (
                    "Sigue los 9 pasos del agent_sequence. "
                    "Carga solo el contexto mínimo necesario. "
                    "Registra en DECISIONS.md SOLO tradeoffs que sobreviven a esta iniciativa. "
                    "Actualiza cada tarea a in_progress antes de codear, a done al terminar. "
                    "Usa placement_test para decidir dónde documentar cada decisión."
                ),
            }, t.elapsed_ms)

        # ── review ────────────────────────────────────────────────────────
        if action == "review":
            if not initiative:
                return ForgeResult.failure(TOOL, ["--initiative is required"], t.elapsed_ms)

            spec_content  = read_file(root, str(spec_path_for(root, initiative).relative_to(root))) or read_file(root, str(spec_path_for(root, None).relative_to(root))) or ""
            tasks_content = read_file(root, str(tasks_path_for(root, initiative).relative_to(root))) or ""
            all_tasks     = [task for task in parse_all_toml_blocks(tasks_content) if task.get("id")]

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

            spec_path    = spec_path_for(root, initiative)
            spec_rel     = str(spec_path.relative_to(root))
            spec_content = read_file(root, spec_rel)
            if spec_content is None:
                return ForgeResult.failure(TOOL, [f"Spec not found: {spec_rel}"], t.elapsed_ms)

            today = _now()
            # Update state + updated_at in the TOML block
            updated = re.sub(r'(state\s*=\s*")[^"]*(")', r'\1done\2', spec_content)
            updated = re.sub(r'(updated_at\s*=\s*")[^"]*(")', rf'\1{today}\2', updated)

            # Append traceability entry
            trace_rel     = context_rel(root, "traceability") or "agents/TRACEABILITY.md"
            trace_path    = root / trace_rel
            trace_content = read_file(root, trace_rel) or "# Traceability\n\n"
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
            if decision_state not in _VALID_DECISION_STATES:
                return ForgeResult.failure(
                    TOOL,
                    [f"Invalid decision_state '{decision_state}'. Valid: {', '.join(_VALID_DECISION_STATES)}"],
                    t.elapsed_ms,
                )
            dec_rel     = context_rel(root, "decisions") or "agents/DECISIONS.md"
            dec_path    = root / dec_rel
            existing    = read_file(root, dec_rel) or "# Decisions\n\n"
            dec_id      = _next_decision_id(existing)
            new_block   = _decision_block(dec_id, title, context, decision, consequences,
                                          owner, state=decision_state)
            updated     = existing.rstrip() + "\n" + new_block
            result      = _write_or_preview(dec_path, updated, write)

            return ForgeResult.success(TOOL, {
                "action":     "decision",
                "id":         dec_id,
                "title":      title,
                "state":      decision_state,
                "placement_test": [f"{q} → {doc}" for q, doc in PLACEMENT_DECISION_TREE],
                **result,
            }, t.elapsed_ms)

        # ── state ─────────────────────────────────────────────────────────
        if action == "state":
            if not initiative or not state:
                return ForgeResult.failure(TOOL, ["--initiative and --state are required for action=state"], t.elapsed_ms)

            if task_id:
                # Update task state in TASKS.md
                tasks_path = tasks_path_for(root, initiative)
                tasks_rel  = str(tasks_path.relative_to(root))
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
                spec_path = spec_path_for(root, initiative)
                spec_rel  = str(spec_path.relative_to(root))
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
    p.add_argument("--state",           default=None,
                   help=f"New state. Spec: {_VALID_SPEC_STATES} | Task: {_VALID_TASK_STATES}")
    p.add_argument("--title",           default=None, help="Decision title (action=decision)")
    p.add_argument("--context",         default=None, help="Decision context (action=decision)")
    p.add_argument("--decision",        default=None, help="The decision made (action=decision)")
    p.add_argument("--consequences",    default=None, help="Consequences of the decision (action=decision)")
    p.add_argument("--decision-state",  default="proposed", dest="decision_state",
                   help=f"Initial state for a new decision: {_VALID_DECISION_STATES} (default: proposed)")
    p.add_argument("--owner",           default="team")
    p.add_argument("--write",           action="store_true",
                   help="Actually write files (default: preview only)")
    p.add_argument("--repo",            default=None)


if __name__ == "__main__":
    make_cli(TOOL, "SpecNative initiative lifecycle: start→plan→implement→review→close", run, _add_args)
