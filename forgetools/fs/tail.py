from __future__ import annotations

"""
fs/tail.py — Extract last N lines from one file or many files matching a glob.

Single file:
    forge fs tail --file app.log
    forge fs tail --file app.log --lines 20

Multiple files (glob):
    forge fs tail --pattern "logs/*.log" --lines 5
    forge fs tail --pattern "src/**/*.java"
"""

import argparse
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "fs.tail"

IGNORE_DIRS: set[str] = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    "target", "dist", "build", ".next", ".cache", "vendor",
    ".idea", ".vscode",
}


def _read_tail(fp: Path, n: int) -> dict:
    try:
        with open(fp, encoding="utf-8", errors="replace") as fh:
            all_lines = fh.readlines()
        snippet = all_lines[-n:] if len(all_lines) >= n else all_lines
        offset  = max(0, len(all_lines) - n)
        return {
            "path":        str(fp),
            "total_lines": len(all_lines),
            "showing":     len(snippet),
            "line_offset": offset + 1,  # 1-based first line shown
            "lines": [
                {"n": offset + i + 1, "text": line.rstrip("\n")}
                for i, line in enumerate(snippet)
            ],
        }
    except OSError as e:
        return {"path": str(fp), "error": str(e)}


def _glob_files(pattern: str, base: Path) -> list[Path]:
    results: list[Path] = []
    try:
        matches = sorted(base.glob(pattern))
        for m in matches:
            if m.is_file() and not any(p in IGNORE_DIRS for p in m.parts):
                results.append(m)
    except Exception:
        pass
    return results


def run(
    *,
    file: str | None = None,
    pattern: str | None = None,
    lines: int = 10,
    path: str = ".",
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if not file and not pattern:
            return ForgeResult.failure(
                TOOL, ["Provide --file or --pattern"], t.elapsed_ms,
                suggestion="forge fs tail --file app.log  OR  forge fs tail --pattern 'logs/*.log'",
            )

        base = Path(cwd or ".").resolve()

        if file:
            fp = Path(file) if Path(file).is_absolute() else base / file
            if not fp.exists():
                return ForgeResult.failure(TOOL, [f"File not found: {fp}"], t.elapsed_ms)
            targets = [fp]
        else:
            root = Path(path) if Path(path).is_absolute() else base / path
            targets = _glob_files(pattern, root)  # type: ignore[arg-type]
            if not targets:
                return ForgeResult.failure(
                    TOOL, [f"No files matched pattern '{pattern}' in {root}"], t.elapsed_ms,
                )

        results = [_read_tail(fp, lines) for fp in targets]

        return ForgeResult.success(TOOL, {
            "lines_requested": lines,
            "files":           len(results),
            "results":         results,
        }, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file",    "-f", default=None, help="Single file to read")
    p.add_argument("--pattern", "-p", default=None, help="Glob pattern (e.g. 'logs/*.log')")
    p.add_argument("--lines",   "-n", type=int, default=10,
                   help="Number of lines from the bottom (default: 10)")
    p.add_argument("--path",    default=".", help="Root for glob resolution (default: .)")
    p.add_argument("--cwd",     default=None, help="Working directory")


if __name__ == "__main__":
    make_cli(TOOL, "Extract last N lines from a file or files matching a glob", run, _add_args)
