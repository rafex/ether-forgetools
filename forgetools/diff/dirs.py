"""forgetools.diff.dirs — Compare two directory trees by content hash."""
from __future__ import annotations

import argparse
import hashlib
import os
from fnmatch import fnmatch
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "diff.dirs"


def run(
    *,
    a: str,
    b: str,
    cwd: str | None = None,
    ignore: str | None = None,
) -> ForgeResult:
    """Compare two directory trees. Returns added, removed, and modified file lists."""
    with Timer() as t:
        try:
            base = Path(cwd) if cwd else Path(".")
            path_a = Path(a) if os.path.isabs(a) else base / a
            path_b = Path(b) if os.path.isabs(b) else base / b

            if not path_a.is_dir():
                return ForgeResult.failure(
                    TOOL, [f"Not a directory: {a}"], t.elapsed_ms,
                    suggestion="Provide a valid directory path",
                )
            if not path_b.is_dir():
                return ForgeResult.failure(
                    TOOL, [f"Not a directory: {b}"], t.elapsed_ms,
                    suggestion="Provide a valid directory path",
                )

            ignore_patterns = (
                [p.strip() for p in ignore.split(",") if p.strip()]
                if ignore
                else []
            )

            files_a = _scan_dir(path_a, ignore_patterns)
            files_b = _scan_dir(path_b, ignore_patterns)

            keys_a = set(files_a)
            keys_b = set(files_b)

            added    = sorted(keys_b - keys_a)
            removed  = sorted(keys_a - keys_b)
            common   = keys_a & keys_b
            modified = sorted(k for k in common if files_a[k] != files_b[k])
            unchanged_count = sum(1 for k in common if files_a[k] == files_b[k])

            return ForgeResult.success(TOOL, {
                "a": str(path_a),
                "b": str(path_b),
                "added":           added,
                "removed":         removed,
                "modified":        modified,
                "unchanged_count": unchanged_count,
                "summary": {
                    "added":     len(added),
                    "removed":   len(removed),
                    "modified":  len(modified),
                    "unchanged": unchanged_count,
                    "total_a":   len(files_a),
                    "total_b":   len(files_b),
                },
            }, t.elapsed_ms)

        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _file_hash(path: Path) -> str:
    h = hashlib.md5(usedforsecurity=False)
    h.update(path.read_bytes())
    return h.hexdigest()


def _scan_dir(root: Path, ignore_patterns: list[str]) -> dict[str, str]:
    """Return {relative_path: md5_hex} for every file under root."""
    result: dict[str, str] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(root))
        if _is_ignored(rel, ignore_patterns):
            continue
        try:
            result[rel] = _file_hash(p)
        except OSError:
            result[rel] = "ERROR"
    return result


def _is_ignored(rel: str, patterns: list[str]) -> bool:
    if not patterns:
        return False
    parts = rel.replace("\\", "/").split("/")
    for pat in patterns:
        if fnmatch(rel, pat):
            return True
        if any(fnmatch(part, pat) for part in parts):
            return True
    return False


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--a", required=True, help="First directory path")
    p.add_argument("--b", required=True, help="Second directory path")
    p.add_argument(
        "--ignore", default=None,
        help="Comma-separated glob patterns to ignore (e.g. '*.pyc,__pycache__,.git')",
    )


if __name__ == "__main__":
    make_cli(TOOL, "Compare two directory trees by content hash", run, _add_args)
