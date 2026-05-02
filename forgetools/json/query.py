"""forgetools.json.query — Query a JSON file or string using dot-notation paths."""
from __future__ import annotations

import argparse
import json
import os
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "json.query"


def run(
    *,
    file: str | None = None,
    path: str = ".",
    data_str: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if file is None and data_str is None:
            return ForgeResult.failure(
                TOOL, ["Either --file or --data-str must be provided"], duration_ms=t.elapsed_ms
            )
        try:
            if data_str is not None:
                obj = json.loads(data_str)
            else:
                resolved = file if os.path.isabs(file) else os.path.join(cwd or os.getcwd(), file)
                with open(resolved, encoding="utf-8") as fh:
                    obj = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            return ForgeResult.failure(TOOL, [str(e)], duration_ms=t.elapsed_ms)

        try:
            result = _resolve(obj, path)
        except (KeyError, IndexError, TypeError, ValueError) as e:
            return ForgeResult.failure(
                TOOL, [f"Path resolution failed: {e}"], duration_ms=t.elapsed_ms
            )

        type_name = type(result).__name__
        data: dict = {"result": result, "path": path, "type": type_name}
        if isinstance(result, list):
            data["count"] = len(result)
        return ForgeResult.success(TOOL, data, t.elapsed_ms)


def _tokenize(path: str) -> list:
    """Convert dot-notation path to list of (key|index) tokens."""
    if path in (".", ""):
        return []
    tokens = []
    # Split on '.' but keep array notations together
    parts = re.split(r"\.(?![^\[]*\])", path.lstrip("."))
    for part in parts:
        if not part:
            continue
        # Handle array iteration '[]' and index '[N]'
        segments = re.split(r"(\[\d*\])", part)
        for seg in segments:
            if not seg:
                continue
            if seg == "[]":
                tokens.append(("iter",))
            elif re.match(r"\[(\d+)\]", seg):
                idx = int(seg[1:-1])
                tokens.append(("index", idx))
            else:
                tokens.append(("key", seg))
    return tokens


def _resolve(obj, path: str):
    tokens = _tokenize(path)
    current = obj
    for token in tokens:
        if token[0] == "key":
            current = current[token[1]]
        elif token[0] == "index":
            current = current[token[1]]
        elif token[0] == "iter":
            if not isinstance(current, list):
                raise TypeError(f"Expected list for '[]', got {type(current).__name__}")
            # Return all items (next token will be applied to each)
            return current
    return current


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", default=None, help="Path to JSON file")
    p.add_argument("--path", default=".", help="Dot-notation path (e.g. '.data[].name')")
    p.add_argument("--data-str", default=None, help="JSON string to query")


if __name__ == "__main__":
    make_cli(TOOL, "Query a JSON file or string using dot-notation paths", run, _add_args)
