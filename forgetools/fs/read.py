"""forgetools.fs.read — Read a file with metadata."""
from __future__ import annotations

import argparse
import os

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "fs.read"


def run(
    *,
    cwd: str | None = None,
    file: str,
    lines: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        path = os.path.join(cwd or ".", file)
        try:
            stat = os.stat(path)
            with open(path, encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()

            if lines:
                start, end = _parse_range(lines, len(all_lines))
                selected = all_lines[start - 1 : end]
            else:
                selected = all_lines

            return ForgeResult.success(
                TOOL,
                {
                    "file": file,
                    "total_lines": len(all_lines),
                    "size_bytes": stat.st_size,
                    "lines_returned": len(selected),
                    "content": "".join(selected),
                },
                t.elapsed_ms,
            )
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, [f"File not found: {file}"], duration_ms=t.elapsed_ms)


def _parse_range(spec: str, total: int) -> tuple[int, int]:
    if "-" in spec:
        parts = spec.split("-", 1)
        return int(parts[0]), int(parts[1])
    n = int(spec)
    return n, n


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True)
    p.add_argument("--lines", default=None, help="Line range e.g. 1-50")


if __name__ == "__main__":
    make_cli(TOOL, "Read a file with metadata", run, _add_args)
