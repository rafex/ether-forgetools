"""forgetools.diff.json — Semantic deep-diff between two JSON files or strings."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "diff.json"


def run(
    *,
    a: str,
    b: str,
    cwd: str | None = None,
    ignore_order: bool = False,
) -> ForgeResult:
    """Semantic diff of two JSON documents.

    Accepts file paths (relative to cwd) or inline JSON strings.
    Returns a list of changes with path, type (added/removed/modified), and values.
    """
    with Timer() as t:
        try:
            data_a = _load(a, cwd)
            data_b = _load(b, cwd)

            changes: list[dict] = []
            _diff(data_a, data_b, "", changes, ignore_order=ignore_order)

            added    = [c for c in changes if c["type"] == "added"]
            removed  = [c for c in changes if c["type"] == "removed"]
            modified = [c for c in changes if c["type"] == "modified"]

            return ForgeResult.success(TOOL, {
                "a": a,
                "b": b,
                "equal":         not changes,
                "total_changes": len(changes),
                "added":         len(added),
                "removed":       len(removed),
                "modified":      len(modified),
                "changes":       changes,
            }, t.elapsed_ms)

        except json.JSONDecodeError as e:
            return ForgeResult.failure(
                TOOL, [f"JSON parse error: {e}"], t.elapsed_ms,
                suggestion="Verify both inputs are valid JSON",
            )
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(ref: str, cwd: str | None) -> Any:
    """Load JSON from a file path or an inline JSON string."""
    base = Path(cwd) if cwd else Path(".")
    p = Path(ref) if os.path.isabs(ref) else base / ref
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    # Treat ref as inline JSON
    return json.loads(ref)


def _diff(
    a: Any,
    b: Any,
    path: str,
    changes: list[dict],
    *,
    ignore_order: bool,
) -> None:
    """Recursively diff two values, appending to changes."""
    # Different types → modified
    if type(a) is not type(b):
        changes.append({"type": "modified", "path": path or ".", "old": a, "new": b})
        return

    if isinstance(a, dict):
        keys_a = set(a)
        keys_b = set(b)
        for k in sorted(str(k) for k in (keys_a - keys_b)):
            child = f"{path}.{k}" if path else k
            changes.append({"type": "removed", "path": child, "old": a[k], "new": None})
        for k in sorted(str(k) for k in (keys_b - keys_a)):
            child = f"{path}.{k}" if path else k
            changes.append({"type": "added", "path": child, "old": None, "new": b[k]})
        for k in sorted(str(k) for k in (keys_a & keys_b)):
            child = f"{path}.{k}" if path else k
            _diff(a[k], b[k], child, changes, ignore_order=ignore_order)

    elif isinstance(a, list):
        if ignore_order:
            # Compare as multisets using repr as a proxy key
            _diff_list_unordered(a, b, path, changes)
        else:
            max_len = max(len(a), len(b))
            for i in range(max_len):
                child = f"{path}[{i}]"
                if i >= len(a):
                    changes.append({"type": "added",   "path": child, "old": None, "new": b[i]})
                elif i >= len(b):
                    changes.append({"type": "removed", "path": child, "old": a[i], "new": None})
                else:
                    _diff(a[i], b[i], child, changes, ignore_order=ignore_order)

    else:
        if a != b:
            changes.append({"type": "modified", "path": path or ".", "old": a, "new": b})


def _diff_list_unordered(
    a: list, b: list, path: str, changes: list[dict]
) -> None:
    """Diff two lists treating them as unordered sets (uses JSON serialisation for hashing)."""
    def _key(v: Any) -> str:
        return json.dumps(v, sort_keys=True, default=str)

    counts_a: dict[str, int] = {}
    counts_b: dict[str, int] = {}
    for v in a:
        counts_a[_key(v)] = counts_a.get(_key(v), 0) + 1
    for v in b:
        counts_b[_key(v)] = counts_b.get(_key(v), 0) + 1

    idx = 0
    for k, count_a in counts_a.items():
        count_b = counts_b.get(k, 0)
        for _ in range(count_a - count_b):
            changes.append({"type": "removed", "path": f"{path}[?]", "old": json.loads(k), "new": None})
        idx += 1

    for k, count_b in counts_b.items():
        count_a = counts_a.get(k, 0)
        for _ in range(count_b - count_a):
            changes.append({"type": "added", "path": f"{path}[?]", "old": None, "new": json.loads(k)})


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--a", required=True, help="First JSON file path or inline JSON string")
    p.add_argument("--b", required=True, help="Second JSON file path or inline JSON string")
    p.add_argument(
        "--ignore-order", action="store_true",
        help="Treat arrays as unordered sets when comparing",
    )


if __name__ == "__main__":
    make_cli(TOOL, "Semantic diff between two JSON documents", run, _add_args)
