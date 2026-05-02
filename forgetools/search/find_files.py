"""forgetools.search.find_files — Find files by name/extension."""
from __future__ import annotations

import argparse
import os

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "search.find_files"

DEFAULT_EXCLUDE = {".git", "node_modules", "target", ".idea", "__pycache__", ".tox", "dist", "build"}


def run(
    *,
    cwd: str | None = None,
    path: str = ".",
    name: str | None = None,
    ext: str | None = None,
    max_results: int = 500,
    exclude: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        base = os.path.join(cwd or ".", path)
        excluded = DEFAULT_EXCLUDE.copy()
        if exclude:
            excluded.update(x.strip() for x in exclude.split(","))

        found = []
        try:
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in excluded]
                for fname in files:
                    if name and name.lower() not in fname.lower():
                        continue
                    if ext and not fname.endswith(ext):
                        continue
                    full = os.path.join(root, fname)
                    rel = os.path.relpath(full, base)
                    stat = os.stat(full)
                    found.append({"path": rel, "size_bytes": stat.st_size})
                    if len(found) >= max_results:
                        break
                if len(found) >= max_results:
                    break
        except PermissionError as e:
            return ForgeResult.failure(TOOL, [str(e)], duration_ms=t.elapsed_ms)

        return ForgeResult.success(
            TOOL,
            {"count": len(found), "files": found, "truncated": len(found) >= max_results},
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".")
    p.add_argument("--name", default=None, help="Filename substring filter")
    p.add_argument("--ext", default=None, help="Extension filter e.g. .java")
    p.add_argument("--max-results", type=int, default=500)
    p.add_argument("--exclude", default=None, help="Comma-separated dirs to exclude")


if __name__ == "__main__":
    make_cli(TOOL, "Find files by name or extension", run, _add_args)
