"""forgetools.fs.read — Read a file with metadata."""
from __future__ import annotations

import argparse
import os
import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "fs.read"


def run(
    *,
    cwd: str | None = None,
    file: str | None = None,
    filePath: str | None = None,
    path: str | None = None,
    lines: str | None = None,
) -> ForgeResult:
    """Read a text file using file, filePath, or path as compatible aliases."""
    with Timer() as t:
        requested_file = file or filePath or path
        if not requested_file:
            return ForgeResult.failure(
                TOOL,
                ["One of 'file', 'filePath', or 'path' is required"],
                duration_ms=t.elapsed_ms,
                suggestion="Pass file='relative/or/absolute/path' to fs_read",
            )

        resolved_path = os.path.join(cwd or ".", requested_file)
        try:
            stat = os.stat(resolved_path)
            backend = "python"
            if shutil.which("bat"):
                backend = "bat"
                cmd = [
                    "bat", "--style=plain", "--paging=never", "--color=never",
                    "--wrap=never",
                ]
                if lines:
                    start, end = _parse_range(lines, 0)
                    cmd += [f"--line-range={start}:{end}"]
                cmd.append(resolved_path)
                rc, content, stderr = run_command(cmd, timeout=30)
                if rc != 0:
                    return ForgeResult.failure(
                        TOOL,
                        [stderr.strip() or f"bat exited with code {rc}"],
                        duration_ms=t.elapsed_ms,
                        suggestion="Install bat or retry with the Python reader",
                    )
                selected = content.splitlines(keepends=True)
                with open(resolved_path, encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
            else:
                with open(resolved_path, encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                if lines:
                    start, end = _parse_range(lines, len(all_lines))
                    selected = all_lines[start - 1 : end]
                else:
                    selected = all_lines

            return ForgeResult.success(
                TOOL,
                {
                    "file": requested_file,
                    "total_lines": len(all_lines),
                    "size_bytes": stat.st_size,
                    "lines_returned": len(selected),
                    "content": "".join(selected),
                    "backend": backend,
                },
                t.elapsed_ms,
            )
        except FileNotFoundError:
            return ForgeResult.failure(
                TOOL,
                [f"File not found: {requested_file}"],
                duration_ms=t.elapsed_ms,
            )


def _parse_range(spec: str, total: int) -> tuple[int, int]:
    if "-" in spec:
        parts = spec.split("-", 1)
        start, end = int(parts[0]), int(parts[1])
        return start, end if end > 0 else total
    n = int(spec)
    return n, n


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True)
    p.add_argument("--lines", default=None, help="Line range e.g. 1-50")


if __name__ == "__main__":
    make_cli(TOOL, "Read a file with metadata", run, _add_args)
