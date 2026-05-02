"""forgetools.edit.replace_lines — Replace a range of lines in a file."""
from __future__ import annotations

import argparse
import os

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "edit.replace_lines"


def run(
    *,
    cwd: str | None = None,
    file: str,
    start: int,
    end: int,
    content: str | None = None,
    content_file: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        path = os.path.join(cwd or ".", file)
        try:
            if content_file:
                with open(content_file, encoding="utf-8") as f:
                    new_content = f.read()
            elif content is not None:
                new_content = content
            else:
                return ForgeResult.failure(TOOL, ["Provide --content or --content-file"])

            with open(path, encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = lines[: start - 1] + [new_content + "\n"] + lines[end:]
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            return ForgeResult.success(TOOL, {"file": file, "replaced_lines": f"{start}-{end}"}, t.elapsed_ms)
        except FileNotFoundError as e:
            return ForgeResult.failure(TOOL, [str(e)], duration_ms=t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True)
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--end", type=int, required=True)
    p.add_argument("--content", default=None)
    p.add_argument("--content-file", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Replace lines in a file", run, _add_args)
