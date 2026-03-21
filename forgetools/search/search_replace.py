"""forgetools.search.search_replace — Bulk find and replace in files."""
from __future__ import annotations

import argparse
import os
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "search.search_replace"

DEFAULT_EXCLUDE = {".git", "node_modules", "target", "__pycache__"}


def run(
    *,
    cwd: str | None = None,
    pattern: str,
    replacement: str,
    path: str = ".",
    ext: str | None = None,
    dry_run: bool = False,
) -> ForgeResult:
    with Timer() as t:
        base = os.path.join(cwd or ".", path)
        regex = re.compile(pattern)
        changes = []

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE]
            for fname in files:
                if ext and not fname.endswith(ext):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    text = fpath_read(fpath)
                except Exception:
                    continue
                new_text, count = regex.subn(replacement, text)
                if count:
                    rel = os.path.relpath(fpath, base)
                    changes.append({"file": rel, "replacements": count})
                    if not dry_run:
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(new_text)

        return ForgeResult.success(
            TOOL,
            {
                "dry_run": dry_run,
                "files_changed": len(changes),
                "total_replacements": sum(c["replacements"] for c in changes),
                "changes": changes,
            },
            t.elapsed_ms,
        )


def fpath_read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pattern", required=True)
    p.add_argument("--replacement", required=True)
    p.add_argument("--path", default=".")
    p.add_argument("--ext", default=None)
    p.add_argument("--dry-run", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "Find and replace across files", run, _add_args)
