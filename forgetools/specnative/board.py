from __future__ import annotations

"""SpecNative delivery board from initiative task files."""

import argparse
import json
from pathlib import Path
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.specnative._core import find_task_files, parse_all_toml_blocks

TOOL = "specnative.board"
BOARD_COLUMNS = ("ready", "in_progress", "blocked", "waiting", "done")


def _task_initiative(path: Path) -> str:
    try:
        return path.parent.name
    except Exception:
        return ""


def _collect_tasks(root: Path, initiative: str | None = None) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for task_file in find_task_files(root):
        if initiative and task_file.parent.name != initiative:
            continue
        text = task_file.read_text(encoding="utf-8")
        for task in parse_all_toml_blocks(text):
            if not task.get("id"):
                continue
            entry = dict(task)
            entry.setdefault("initiative", _task_initiative(task_file))
            entry["_path"] = str(task_file.relative_to(root))
            tasks.append(entry)
    return sorted(tasks, key=lambda item: (str(item.get("initiative", "")), str(item.get("id", ""))))


def _dependency_waiting(task: dict[str, Any], done_ids: set[str]) -> list[str]:
    deps = task.get("dependencies") or []
    if isinstance(deps, str):
        deps = [deps] if deps else []
    return [str(dep) for dep in deps if str(dep) not in done_ids]


def _board(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    done_ids = {str(task["id"]) for task in tasks if task.get("state") == "done"}
    columns: dict[str, list[dict[str, Any]]] = {column: [] for column in BOARD_COLUMNS}
    for task in tasks:
        entry = dict(task)
        unresolved = _dependency_waiting(entry, done_ids)
        if unresolved:
            entry["unresolved_dependencies"] = unresolved
        state = str(entry.get("state") or "unknown")
        if state == "todo":
            column = "waiting" if unresolved else "ready"
        elif state in {"in_progress", "blocked", "done"}:
            column = state
        else:
            column = "waiting"
        entry["board_column"] = column
        entry["completion_evidence_missing"] = state == "done" and not entry.get("completion_evidence")
        columns[column].append(entry)
    priority_order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
    for column_tasks in columns.values():
        column_tasks.sort(key=lambda item: (priority_order.get(str(item.get("priority", "p2")), 99), str(item.get("id", ""))))
    return {
        "schema_version": "1.0",
        "source_of_truth": "spec-native/tasks/**/TASKS.md",
        "count": len(tasks),
        "columns": columns,
        "lanes": {name: items for name, items in columns.items() if items},
        "states": {name: len(items) for name, items in columns.items() if items},
    }


def _format_markdown(board: dict[str, Any]) -> str:
    lines = ["# SpecNative Board", "", "> Generated projection. Update task TOML metadata, never this view.", ""]
    lines.extend(["| Lane | Task | Initiative | Owner | Summary |", "|---|---|---|---|---|"])
    for lane in BOARD_COLUMNS:
        tasks = board["columns"][lane]
        for task in tasks:
            title = task.get("title") or task.get("close_criteria") or ""
            lines.append(
                f"| {lane} | `{task.get('id', '')}` | {task.get('initiative', '')} | "
                f"{task.get('owner', '')} | {str(title).replace('|', '/')[:120]} |"
            )
    return "\n".join(lines)


def _format_mermaid(board: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    for lane in BOARD_COLUMNS:
        tasks = board["columns"][lane]
        lane_id = lane.replace("-", "_")
        lines.append(f'  subgraph {lane_id}["{lane}"]')
        for task in tasks:
            node_id = str(task.get("id", "")).replace("-", "_")
            label = f"{task.get('id', '')}\\n{task.get('initiative', '')}"
            lines.append(f'    {node_id}["{label}"]')
        lines.append("  end")
    for tasks in board["columns"].values():
        for task in tasks:
            node_id = str(task.get("id", "")).replace("-", "_")
            deps = task.get("dependencies") or []
            if isinstance(deps, str):
                deps = [deps] if deps else []
            for dep in deps:
                dep_id = str(dep).replace("-", "_")
                lines.append(f"  {dep_id} --> {node_id}")
    return "\n".join(lines)


def run(
    *,
    initiative: str | None = None,
    format: str = "json",
    repo: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    """Build a SpecNative delivery board from TASKS.md files."""
    with Timer() as t:
        root = Path(repo or cwd or ".").resolve()
        if not root.is_dir():
            return ForgeResult.failure(TOOL, [f"Directory not found: {root}"], t.elapsed_ms)
        if format not in ("json", "markdown", "mermaid"):
            return ForgeResult.failure(TOOL, ["format must be json, markdown, or mermaid"], t.elapsed_ms)

        tasks = _collect_tasks(root, initiative)
        board = _board(tasks)
        if format == "markdown":
            board["content"] = _format_markdown(board)
        elif format == "mermaid":
            board["content"] = _format_mermaid(board)
        else:
            board["content"] = json.dumps(board, indent=2)
        return ForgeResult.success(TOOL, {"initiative": initiative, "format": format, **board}, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--initiative", default=None)
    p.add_argument("--format", default="json", choices=["json", "markdown", "mermaid"])
    p.add_argument("--repo", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Build a SpecNative delivery board from task files", run, _add_args)
