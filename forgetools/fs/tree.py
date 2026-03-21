"""forgetools.fs.tree — Directory tree with smart filters."""
from __future__ import annotations

import argparse
import os

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "fs.tree"
DEFAULT_EXCLUDE = {".git", "node_modules", "target", ".idea", "__pycache__", ".tox", "dist", "build", ".gradle"}


def run(
    *,
    cwd: str | None = None,
    path: str = ".",
    max_depth: int = 4,
    exclude: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        base = os.path.join(cwd or ".", path)
        excluded = DEFAULT_EXCLUDE.copy()
        if exclude:
            excluded.update(x.strip() for x in exclude.split(","))
        tree = _build(base, base, max_depth, excluded, 0)
        return ForgeResult.success(TOOL, {"root": path, "tree": tree}, t.elapsed_ms)


def _build(root: str, base: str, max_depth: int, excluded: set, depth: int) -> list[dict]:
    if depth >= max_depth:
        return []
    try:
        entries = sorted(os.scandir(root), key=lambda e: (not e.is_dir(), e.name))
    except PermissionError:
        return []
    result = []
    for entry in entries:
        if entry.name in excluded:
            continue
        node: dict = {"name": entry.name, "type": "dir" if entry.is_dir() else "file"}
        if entry.is_dir():
            node["children"] = _build(entry.path, base, max_depth, excluded, depth + 1)
        else:
            node["size_bytes"] = entry.stat().st_size
        result.append(node)
    return result


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".")
    p.add_argument("--max-depth", type=int, default=4)
    p.add_argument("--exclude", default=None, help="Comma-separated dirs to exclude")


if __name__ == "__main__":
    make_cli(TOOL, "Show directory tree with filters", run, _add_args)
