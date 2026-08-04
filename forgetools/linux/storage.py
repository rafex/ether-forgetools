"""Inspect Linux filesystem usage, mounts, inodes, and largest paths."""
from __future__ import annotations

import argparse
import os
import shlex
from pathlib import Path
import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "linux.storage"
ACTIONS = ("usage", "inodes", "mounts", "largest")


def run(*, action: str = "usage", path: str = ".", max_entries: int = 20,
        max_depth: int = 3, cwd: str | None = None) -> ForgeResult:
    with Timer() as timer:
        if action not in ACTIONS:
            return ForgeResult.failure(TOOL, [f"Unknown action: {action}"], timer.elapsed_ms,
                                       suggestion=f"Use one of: {', '.join(ACTIONS)}")
        target = Path(path if os.path.isabs(path) else os.path.join(cwd or os.getcwd(), path)).absolute()
        try:
            if action == "usage":
                data = _usage(target)
            elif action == "inodes":
                data = _inodes(target)
            elif action == "mounts":
                data = _mounts()
            else:
                data = _largest(target, max_entries=max(1, min(max_entries, 1000)), max_depth=max(0, max_depth))
        except OSError as exc:
            return ForgeResult.failure(TOOL, [str(exc)], timer.elapsed_ms)
        return ForgeResult.success(TOOL, data, timer.elapsed_ms)


def _usage(path: Path) -> dict:
    usage = shutil.disk_usage(path)
    return {
        "path": str(path),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "used_percent": round((usage.used / usage.total) * 100, 2) if usage.total else 0,
    }


def _inodes(path: Path) -> dict:
    stat = os.statvfs(path)
    total = stat.f_files
    free = stat.f_ffree
    return {
        "path": str(path),
        "total": total,
        "free": free,
        "used": max(total - free, 0),
        "used_percent": round(((total - free) / total) * 100, 2) if total else 0,
    }


def _mounts() -> dict:
    mounts: list[dict[str, str]] = []
    try:
        lines = Path("/proc/self/mounts").read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines:
            parts = shlex.split(line)
            if len(parts) >= 4:
                mounts.append({"device": parts[0], "mountpoint": parts[1], "filesystem": parts[2], "options": parts[3]})
    except FileNotFoundError:
        return {"available": False, "mounts": []}
    return {"available": True, "count": len(mounts), "mounts": mounts}


def _largest(path: Path, *, max_entries: int, max_depth: int) -> dict:
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    sizes: dict[Path, int] = {path: 0}
    for root, dirs, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        depth = len(root_path.relative_to(path).parts)
        dirs[:] = [name for name in dirs if not (root_path / name).is_symlink() and depth < max_depth]
        for name in files:
            item = root_path / name
            try:
                size = item.stat(follow_symlinks=False).st_size
            except OSError:
                continue
            sizes[item] = size
            current = root_path
            while True:
                sizes[current] = sizes.get(current, 0) + size
                if current == path:
                    break
                current = current.parent
    rows = sorted(
        ({"path": str(item), "size_bytes": size} for item, size in sizes.items() if item != path),
        key=lambda row: row["size_bytes"], reverse=True,
    )[:max_entries]
    return {"path": str(path), "max_depth": max_depth, "entries": rows}


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--action", default="usage", choices=ACTIONS)
    parser.add_argument("--path", default=".")
    parser.add_argument("--max-entries", type=int, default=20)
    parser.add_argument("--max-depth", type=int, default=3)


if __name__ == "__main__":
    make_cli(TOOL, "Inspect Linux filesystem usage, mounts, inodes, and largest paths", run, _add_args)
