from __future__ import annotations

"""SpecNative backlog capture helpers."""

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.specnative._core import parse_all_toml_blocks, spec_path_for, tasks_path_for, uses_modern_layout

TOOL = "specnative.backlog"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _split_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in re.split(r"[,;\n]+", value) if part.strip()]


def _toml_array(values: list[str]) -> str:
    return "[" + ", ".join(f'"{value.replace(chr(34), chr(92) + chr(34))}"' for value in values) + "]"


def _next_task_id(existing: str, initiative: str) -> str:
    prefix = f"TASK-{initiative.upper()[:10]}"
    ids = [int(match) for match in re.findall(rf"\b{re.escape(prefix)}-(\d+)\b", existing)]
    return f"{prefix}-{(max(ids) + 1) if ids else 1:03d}"


def _backlog_path(root: Path) -> Path:
    return root / ("spec-native/intake/IDEAS.md" if uses_modern_layout(root) else "agents/BACKLOG.md")


def _existing_task_ids(root: Path) -> set[str]:
    base = root / ("spec-native/tasks" if uses_modern_layout(root) else "tasks")
    ids: set[str] = set()
    if not base.is_dir():
        return ids
    for path in base.rglob("TASKS.md"):
        for task in parse_all_toml_blocks(path.read_text(encoding="utf-8")):
            if task.get("id"):
                ids.add(str(task["id"]))
    return ids


def _task_block(
    *,
    task_id: str,
    initiative: str,
    title: str,
    description: str,
    priority: str,
    labels: list[str],
    owner: str,
    dependencies: list[str],
    expected_files: list[str],
    close_criteria: str,
    validation: list[str],
) -> str:
    today = _today()
    return f"""
## {task_id}: {title}

```toml
artifact_type = "task"
id = "{task_id}"
state = "todo"
owner = "{owner}"
initiative = "{initiative}"
priority = "{priority}"
labels = {_toml_array(labels)}
dependencies = {_toml_array(dependencies)}
expected_files = {_toml_array(expected_files)}
close_criteria = "{close_criteria or description or title}"
validation = {_toml_array(validation)}
completion_evidence = []
created_at = "{today}"
updated_at = "{today}"
```

**Description:** {description or title}

---
"""


def _idea_block(title: str, description: str, priority: str, labels: list[str], owner: str) -> str:
    today = _today()
    return (
        f"\n## {today}: {title}\n\n"
        f"- owner: {owner}\n"
        f"- priority: {priority}\n"
        f"- labels: {', '.join(labels) if labels else 'none'}\n\n"
        f"{description or title}\n"
    )


def run(
    *,
    initiative: str | None = None,
    title: str | None = None,
    description: str = "",
    kind: str = "task",
    priority: str = "p2",
    labels: str = "",
    owner: str = "team",
    dependencies: str = "",
    expected_files: str = "",
    close_criteria: str = "",
    validation: str = "",
    write: bool = False,
    repo: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    """Capture a SpecNative backlog item as a task preview or backlog note."""
    with Timer() as t:
        root = Path(repo or cwd or ".").resolve()
        if not root.is_dir():
            return ForgeResult.failure(TOOL, [f"Directory not found: {root}"], t.elapsed_ms)
        if not title:
            return ForgeResult.failure(TOOL, ["title is required"], t.elapsed_ms)
        if kind not in ("task", "idea"):
            return ForgeResult.failure(TOOL, ["kind must be task or idea"], t.elapsed_ms)
        if priority not in {"p0", "p1", "p2", "p3"}:
            return ForgeResult.failure(TOOL, ["Invalid priority. Use p0, p1, p2, or p3"], t.elapsed_ms)

        label_list = _split_list(labels)
        if kind == "task":
            if not initiative or not spec_path_for(root, initiative).exists():
                kind = "idea"
            elif not close_criteria.strip() or not _split_list(validation):
                return ForgeResult.failure(
                    TOOL,
                    ["close_criteria and at least one validation are required to create an executable task"],
                    t.elapsed_ms,
                    suggestion="Call without initiative or with kind=idea to capture triaged intake instead.",
                )

        if kind == "task":
            dependency_list = _split_list(dependencies)
            missing_dependencies = [dependency for dependency in dependency_list if dependency not in _existing_task_ids(root)]
            if missing_dependencies:
                return ForgeResult.failure(
                    TOOL,
                    [f"Cannot create task: dependencies do not exist: {', '.join(missing_dependencies)}"],
                    t.elapsed_ms,
                )
            path = tasks_path_for(root, initiative)
            existing = path.read_text(encoding="utf-8") if path.exists() else f"# Tasks: {initiative}\n"
            task_id = _next_task_id(existing, initiative)
            block = _task_block(
                task_id=task_id,
                initiative=initiative,
                title=title,
                description=description,
                priority=priority,
                labels=label_list,
                owner=owner,
                dependencies=dependency_list,
                expected_files=_split_list(expected_files),
                close_criteria=close_criteria,
                validation=_split_list(validation),
            )
            content = existing.rstrip() + "\n" + block
            data = {"kind": kind, "id": task_id, "initiative": initiative, "path": str(path), "content": None if write else content}
        if kind == "idea":
            path = _backlog_path(root)
            existing = path.read_text(encoding="utf-8") if path.exists() else "# Backlog\n"
            content = existing.rstrip() + "\n" + _idea_block(title, description, priority, label_list, owner)
            data = {"kind": kind, "path": str(path), "content": None if write else content}

        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        data["written"] = write
        return ForgeResult.success(TOOL, data, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--initiative", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--description", default="")
    p.add_argument("--kind", default="task", choices=["task", "idea"])
    p.add_argument("--priority", default="p2")
    p.add_argument("--labels", default="")
    p.add_argument("--owner", default="team")
    p.add_argument("--dependencies", default="")
    p.add_argument("--expected-files", dest="expected_files", default="")
    p.add_argument("--close-criteria", dest="close_criteria", default="")
    p.add_argument("--validation", default="")
    p.add_argument("--write", action="store_true")
    p.add_argument("--repo", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Capture a SpecNative backlog item", run, _add_args)
