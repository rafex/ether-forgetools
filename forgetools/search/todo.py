"""Find TODO-style markers quickly with ripgrep and a bounded fallback."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "search.todo"
PATTERN = re.compile(r"(TODO|FIXME|HACK|XXX|NOTE|BUG)[\s:]?(.*)", re.IGNORECASE)
DEFAULT_EXCLUDE = (
    ".git",
    "node_modules",
    "target",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "vendor",
    "coverage",
    ".opencode/worktrees",
    ".claude/worktrees",
    ".git/worktrees",
)


def run(*, cwd: str | None = None, path: str = ".", ext: str | None = None,
        max_results: int = 200, include_hidden: bool = True,
        respect_ignore: bool = True) -> ForgeResult:
    """Find TODO markers without traversing dependency, cache, or worktree trees."""
    with Timer() as timer:
        if max_results < 1:
            return ForgeResult.failure(TOOL, ["max_results must be greater than zero"], timer.elapsed_ms)
        base = os.path.abspath(os.path.join(cwd or os.getcwd(), path)) if not os.path.isabs(path) else os.path.abspath(path)
        try:
            if shutil.which("rg"):
                items, backend, truncated = _run_rg(
                    cwd=cwd, path=path, base=base, ext=ext, max_results=max_results,
                    include_hidden=include_hidden, respect_ignore=respect_ignore,
                )
            else:
                items, backend, truncated = _run_fallback(
                    base=base, ext=ext, max_results=max_results,
                )
        except (OSError, ValueError) as exc:
            return ForgeResult.failure(TOOL, [str(exc)], timer.elapsed_ms,
                                       suggestion="Install ripgrep (rg) or reduce the search path")

        by_tag: dict[str, int] = {}
        for item in items:
            by_tag[item["tag"]] = by_tag.get(item["tag"], 0) + 1
        return ForgeResult.success(
            TOOL,
            {
                "path": base,
                "count": len(items),
                "by_tag": by_tag,
                "items": items,
                "backend": backend,
                "max_results": max_results,
                "truncated": truncated,
            },
            timer.elapsed_ms,
        )


def _run_rg(*, cwd: str | None, path: str, base: str, ext: str | None,
            max_results: int, include_hidden: bool, respect_ignore: bool) -> tuple[list[dict], str, bool]:
    command = ["rg", "--json"]
    if include_hidden:
        command.append("--hidden")
    if not respect_ignore:
        command.append("--no-ignore-vcs")
    if ext:
        command += ["--glob", f"*{ext if ext.startswith('.') else f'.{ext}'}"]
    for excluded in DEFAULT_EXCLUDE:
        command += ["--glob", f"!**/{excluded}/**"]
    # rg's max-count is per file; _parse_rg caps the global response as well.
    command += ["--max-count", str(max_results), "--", PATTERN.pattern, path]
    rc, stdout, stderr = run_command(command, cwd=cwd, timeout=45)
    if rc > 1:
        raise OSError(stderr.strip() or f"rg exited with code {rc}")
    items = _parse_rg(stdout, base, max_results, output_root=os.path.abspath(cwd or os.getcwd()))
    return items, "rg-json", len(items) >= max_results


def _parse_rg(stdout: str, base: str, max_results: int, output_root: str) -> list[dict]:
    items: list[dict] = []
    for raw_line in stdout.splitlines():
        if len(items) >= max_results:
            break
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "match":
            continue
        data = event.get("data") or {}
        raw_path = ((data.get("path") or {}).get("text"))
        line = ((data.get("lines") or {}).get("text", "")).rstrip("\n")
        marker = PATTERN.search(line)
        if not raw_path or not marker:
            continue
        item_path = raw_path if os.path.isabs(raw_path) else os.path.abspath(os.path.join(output_root, raw_path))
        items.append({
            "file": os.path.relpath(item_path, base),
            "line": data.get("line_number"),
            "tag": marker.group(1).upper(),
            "text": marker.group(2).strip(),
        })
    return items


def _run_fallback(*, base: str, ext: str | None, max_results: int) -> tuple[list[dict], str, bool]:
    results: list[dict] = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [directory for directory in dirs if not _excluded(base, root, directory)]
        for fname in files:
            if ext and not fname.endswith(ext if ext.startswith(".") else f".{ext}"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as handle:
                    for line_number, line in enumerate(handle, 1):
                        marker = PATTERN.search(line)
                        if marker:
                            results.append({
                                "file": os.path.relpath(fpath, base),
                                "line": line_number,
                                "tag": marker.group(1).upper(),
                                "text": marker.group(2).strip(),
                            })
                            if len(results) >= max_results:
                                return results, "python-fallback", True
            except (OSError, UnicodeError):
                continue
    return results, "python-fallback", False


def _excluded(base: str, root: str, directory: str) -> bool:
    if directory in DEFAULT_EXCLUDE:
        return True
    relative = os.path.relpath(os.path.join(root, directory), base)
    return any(relative == excluded or relative.startswith(f"{excluded}{os.sep}") for excluded in DEFAULT_EXCLUDE)


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", default=".")
    parser.add_argument("--ext", default=None, help="Filter by extension e.g. .java")
    parser.add_argument("--max-results", type=int, default=200)
    parser.add_argument("--no-hidden", dest="include_hidden", action="store_false", default=True)
    parser.add_argument("--no-respect-ignore", dest="respect_ignore", action="store_false", default=True)


if __name__ == "__main__":
    make_cli(TOOL, "Find TODOs and FIXMEs quickly with bounded output", run, _add_args)
