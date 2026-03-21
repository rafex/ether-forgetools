"""forgetools.edit.insert — Insert lines into a file at a specific position."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "edit.insert"


def run(
    *,
    cwd: str | None = None,
    file: str,
    after_line: int,
    content: str,
) -> ForgeResult:
    import os
    with Timer() as t:
        path = os.path.join(cwd or ".", file)
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = lines[:after_line] + [content + "\n"] + lines[after_line:]
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            return ForgeResult.success(TOOL, {"file": file, "inserted_after_line": after_line}, t.elapsed_ms)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, [f"File not found: {file}"], duration_ms=t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True)
    p.add_argument("--after-line", type=int, required=True)
    p.add_argument("--content", required=True)


if __name__ == "__main__":
    make_cli(TOOL, "Insert a line into a file", run, _add_args)
