"""forgetools.fs.disk_usage - Structured disk usage using ncdu when available."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "fs.disk_usage"
DEFAULT_EXCLUDE = {".git", "node_modules", "target", ".venv", "__pycache__"}


def run(
    *,
    path: str = ".",
    cwd: str | None = None,
    max_entries: int = 100,
    exclude: str | None = None,
    apparent_size: bool = False,
) -> ForgeResult:
    with Timer() as t:
        base = Path(cwd or ".").resolve()
        root = Path(path) if Path(path).is_absolute() else base / path
        if not root.exists():
            return ForgeResult.failure(TOOL, [f"Path not found: {root}"], t.elapsed_ms)

        excluded = DEFAULT_EXCLUDE.copy()
        if exclude:
            excluded.update(item.strip() for item in exclude.split(",") if item.strip())

        if shutil.which("ncdu"):
            result = _run_ncdu(root, max_entries, excluded, apparent_size, t)
            if result is not None:
                return result
        return _run_python(root, max_entries, excluded, apparent_size, t)


def _run_ncdu(
    root: Path,
    max_entries: int,
    excluded: set[str],
    apparent_size: bool,
    timer: Timer,
) -> ForgeResult | None:
    cmd = ["ncdu", "-0", "-o", "-", "-rr"]
    if apparent_size:
        cmd.append("--apparent-size")
    for item in sorted(excluded):
        cmd += ["--exclude", item]
    cmd.append(str(root))
    try:
        rc, stdout, stderr = run_command(cmd, timeout=120)
    except (FileNotFoundError, OSError):
        return None
    if rc != 0:
        return ForgeResult.failure(
            TOOL,
            [stderr.strip() or f"ncdu exited with code {rc}"],
            duration_ms=timer.elapsed_ms,
            suggestion="Install ncdu or retry with the Python fallback",
        )
    try:
        payload = json.loads(stdout)
        entries = _parse_ncdu(payload[3] if len(payload) > 3 else [], str(root), apparent_size)
    except (ValueError, IndexError, TypeError, json.JSONDecodeError) as exc:
        return ForgeResult.failure(TOOL, [f"Invalid ncdu JSON: {exc}"], timer.elapsed_ms)
    entries.sort(key=lambda item: item["size_bytes"], reverse=True)
    return ForgeResult.success(
        TOOL,
        {
            "path": str(root),
            "backend": "ncdu",
            "apparent_size": apparent_size,
            "total_size_bytes": next(
                (item["size_bytes"] for item in entries if item["path"] == str(root)),
                0,
            ),
            "entries": entries[:max_entries] if max_entries > 0 else entries,
            "truncated": max_entries > 0 and len(entries) > max_entries,
        },
        timer.elapsed_ms,
    )


def _parse_ncdu(nodes: list, root: str, apparent_size: bool) -> list[dict]:
    """Parse ncdu 2 JSON, where each nested array represents one directory."""
    if not nodes or not isinstance(nodes[0], dict):
        return []
    root_node = nodes[0]
    children, total = _parse_children(nodes[1:], root, apparent_size)
    root_entry = {
        "path": root,
        "name": str(root_node.get("name", Path(root).name)),
        "size_bytes": total,
        "type": "dir",
    }
    return [root_entry, *children]


def _parse_children(nodes: list, parent: str, apparent_size: bool) -> tuple[list[dict], int]:
    result: list[dict] = []
    total = 0
    for node in nodes:
        if isinstance(node, list):
            directory_entries, size = _parse_directory(node, parent, apparent_size)
            result.extend(directory_entries)
            total += size
            continue
        if not isinstance(node, dict):
            continue
        name = str(node.get("name", ""))
        path = os.path.join(parent, name)
        key = "asize" if apparent_size or node.get("dsize") is None else "dsize"
        size = int(node.get(key, 0))
        result.append({"path": path, "name": name, "size_bytes": size, "type": "file"})
        total += size
    return result, total


def _parse_directory(nodes: list, parent: str, apparent_size: bool) -> tuple[list[dict], int]:
    if not nodes or not isinstance(nodes[0], dict):
        return [], 0
    directory = nodes[0]
    name = str(directory.get("name", ""))
    path = os.path.join(parent, name)
    children, total = _parse_children(nodes[1:], path, apparent_size)
    if not children:
        key = "asize" if apparent_size or directory.get("dsize") is None else "dsize"
        total = int(directory.get(key, 0))
    entry = {"path": path, "name": name, "size_bytes": total, "type": "dir"}
    return [entry, *children], total


def _run_python(
    root: Path,
    max_entries: int,
    excluded: set[str],
    apparent_size: bool,
    timer: Timer,
) -> ForgeResult:
    entries: list[dict] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in excluded]
        current_path = Path(current)
        total = 0
        for name in files:
            try:
                stat = (current_path / name).stat()
                total += stat.st_size if apparent_size else stat.st_blocks * 512
            except OSError:
                continue
        entries.append({
            "path": str(current_path),
            "name": current_path.name,
            "size_bytes": total,
            "type": "dir",
        })
    entries.sort(key=lambda item: item["size_bytes"], reverse=True)
    return ForgeResult.success(
        TOOL,
        {
            "path": str(root),
            "backend": "python",
            "apparent_size": apparent_size,
            "total_size_bytes": next(
                (item["size_bytes"] for item in entries if item["path"] == str(root)),
                0,
            ),
            "entries": entries[:max_entries] if max_entries > 0 else entries,
            "truncated": max_entries > 0 and len(entries) > max_entries,
        },
        timer.elapsed_ms,
    )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".")
    p.add_argument("--max-entries", type=int, default=100)
    p.add_argument("--exclude", default=None, help="Comma-separated names to exclude")
    p.add_argument("--apparent-size", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "Measure directory usage with ncdu JSON export or Python fallback", run, _add_args)
