"""forgetools.diff.yaml — Semantic deep-diff between two YAML files."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "diff.yaml"


def run(
    *,
    a: str,
    b: str,
    cwd: str | None = None,
    ignore_order: bool = False,
) -> ForgeResult:
    """Semantic diff of two YAML documents.

    Accepts file paths relative to cwd or absolute paths.
    Returns a list of changes with path, type (added/removed/modified), and values.
    Requires PyYAML (pip install pyyaml).
    """
    with Timer() as t:
        try:
            import yaml  # type: ignore[import]
        except ImportError:
            return ForgeResult.failure(
                TOOL,
                ["PyYAML not installed"],
                t.elapsed_ms,
                suggestion="pip install pyyaml",
            )

        try:
            data_a = _load(a, cwd, yaml)
            data_b = _load(b, cwd, yaml)

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

        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(ref: str, cwd: str | None, yaml: Any) -> Any:
    base = Path(cwd) if cwd else Path(".")
    p = Path(ref) if os.path.isabs(ref) else base / ref
    if p.exists():
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    # Fallback: treat ref as inline YAML / JSON string
    return yaml.safe_load(ref)


def _diff(
    a: Any,
    b: Any,
    path: str,
    changes: list[dict],
    *,
    ignore_order: bool,
) -> None:
    # Different types → modified
    if type(a) is not type(b):
        changes.append({"type": "modified", "path": path or ".", "old": _safe(a), "new": _safe(b)})
        return

    if isinstance(a, dict):
        keys_a = set(str(k) for k in a)
        keys_b = set(str(k) for k in b)

        for k in sorted(keys_a - keys_b):
            child = f"{path}.{k}" if path else k
            changes.append({"type": "removed", "path": child, "old": _safe(a[k]), "new": None})
        for k in sorted(keys_b - keys_a):
            child = f"{path}.{k}" if path else k
            changes.append({"type": "added", "path": child, "old": None, "new": _safe(b[k])})
        for k in sorted(keys_a & keys_b):
            child = f"{path}.{k}" if path else k
            _diff(a[k], b[k], child, changes, ignore_order=ignore_order)

    elif isinstance(a, list):
        if ignore_order:
            _diff_list_unordered(a, b, path, changes)
        else:
            max_len = max(len(a), len(b))
            for i in range(max_len):
                child = f"{path}[{i}]"
                if i >= len(a):
                    changes.append({"type": "added",   "path": child, "old": None, "new": _safe(b[i])})
                elif i >= len(b):
                    changes.append({"type": "removed", "path": child, "old": _safe(a[i]), "new": None})
                else:
                    _diff(a[i], b[i], child, changes, ignore_order=ignore_order)

    else:
        if a != b:
            changes.append({"type": "modified", "path": path or ".", "old": _safe(a), "new": _safe(b)})


def _safe(v: Any) -> Any:
    """Convert YAML-native types (date, etc.) to serialisable form."""
    import datetime
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    return v


def _diff_list_unordered(
    a: list, b: list, path: str, changes: list[dict]
) -> None:
    import json

    def _key(v: Any) -> str:
        return json.dumps(_safe(v), sort_keys=True, default=str)

    counts_a: dict[str, int] = {}
    counts_b: dict[str, int] = {}
    raw_a: dict[str, Any] = {}
    raw_b: dict[str, Any] = {}

    for v in a:
        k = _key(v)
        counts_a[k] = counts_a.get(k, 0) + 1
        raw_a[k] = v
    for v in b:
        k = _key(v)
        counts_b[k] = counts_b.get(k, 0) + 1
        raw_b[k] = v

    for k, count_a in counts_a.items():
        count_b = counts_b.get(k, 0)
        for _ in range(count_a - count_b):
            changes.append({"type": "removed", "path": f"{path}[?]", "old": _safe(raw_a[k]), "new": None})

    for k, count_b in counts_b.items():
        count_a = counts_a.get(k, 0)
        for _ in range(count_b - count_a):
            changes.append({"type": "added", "path": f"{path}[?]", "old": None, "new": _safe(raw_b[k])})


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--a", required=True, help="First YAML file path")
    p.add_argument("--b", required=True, help="Second YAML file path or inline YAML string")
    p.add_argument(
        "--ignore-order", action="store_true",
        help="Treat sequences as unordered sets when comparing",
    )


if __name__ == "__main__":
    make_cli(TOOL, "Semantic diff between two YAML documents", run, _add_args)
