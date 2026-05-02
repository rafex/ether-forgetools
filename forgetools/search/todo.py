"""forgetools.search.todo — Find TODOs, FIXMEs, HACKs in code."""
from __future__ import annotations

import argparse
import os
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "search.todo"
PATTERN = re.compile(r"(TODO|FIXME|HACK|XXX|NOTE|BUG)[\s:](.*)", re.IGNORECASE)
DEFAULT_EXCLUDE = {".git", "node_modules", "target", "__pycache__"}


def run(*, cwd: str | None = None, path: str = ".", ext: str | None = None) -> ForgeResult:
    with Timer() as t:
        base = os.path.join(cwd or ".", path)
        results = []
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE]
            for fname in files:
                if ext and not fname.endswith(ext):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            m = PATTERN.search(line)
                            if m:
                                results.append({
                                    "file": os.path.relpath(fpath, base),
                                    "line": i,
                                    "tag": m.group(1).upper(),
                                    "text": m.group(2).strip(),
                                })
                except Exception:
                    continue

        by_tag: dict[str, int] = {}
        for r in results:
            by_tag[r["tag"]] = by_tag.get(r["tag"], 0) + 1

        return ForgeResult.success(TOOL, {"count": len(results), "by_tag": by_tag, "items": results}, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".")
    p.add_argument("--ext", default=None, help="Filter by extension e.g. .java")


if __name__ == "__main__":
    make_cli(TOOL, "Find TODOs and FIXMEs in code", run, _add_args)
