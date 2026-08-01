"""forgetools.search.search_replace — Bulk find and replace in files."""
from __future__ import annotations

import argparse
import os
import re
import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "search.search_replace"

DEFAULT_EXCLUDE = {".git", "node_modules", "target", "__pycache__"}


def run(
    *,
    cwd: str | None = None,
    pattern: str,
    replacement: str,
    path: str = ".",
    ext: str | None = None,
    dry_run: bool = False,
) -> ForgeResult:
    with Timer() as t:
        base = os.path.join(cwd or ".", path)
        regex = re.compile(pattern)
        changes = []

        candidates = _candidate_files(base, pattern, ext)
        files_to_scan = candidates if candidates is not None else _walk_files(base, ext)

        for fpath in files_to_scan:
            try:
                text = fpath_read(fpath)
            except Exception:
                continue
            new_text, count = regex.subn(replacement, text)
            if count:
                rel = os.path.relpath(fpath, base)
                changes.append({"file": rel, "replacements": count})
                if not dry_run:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_text)

        return ForgeResult.success(
            TOOL,
            {
                "dry_run": dry_run,
                "files_changed": len(changes),
                "total_replacements": sum(c["replacements"] for c in changes),
                "changes": changes,
                "backend": "rg" if candidates is not None else "python",
            },
            t.elapsed_ms,
        )


def _walk_files(base: str, ext: str | None) -> list[str]:
    files_to_scan = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE]
        for fname in files:
            if not ext or fname.endswith(ext):
                files_to_scan.append(os.path.join(root, fname))
    return files_to_scan


def _candidate_files(base: str, pattern: str, ext: str | None) -> list[str] | None:
    """Ask rg for candidate files so Python opens only files with a match."""
    if not shutil.which("rg"):
        return None
    cmd = ["rg", "--files-with-matches", "--hidden", "--no-ignore-vcs"]
    if ext:
        cmd += ["--glob", f"*{ext}"]
    for excluded in (".git", "node_modules", "target", "__pycache__"):
        cmd += ["--glob", f"!{excluded}/**"]
    cmd += [pattern, base]
    try:
        rc, stdout, _ = run_command(cmd, timeout=60)
    except (FileNotFoundError, OSError):
        return None
    if rc not in (0, 1):
        return None
    return [line for line in stdout.splitlines() if line]


def fpath_read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pattern", required=True)
    p.add_argument("--replacement", required=True)
    p.add_argument("--path", default=".")
    p.add_argument("--ext", default=None)
    p.add_argument("--dry-run", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "Find and replace across files", run, _add_args)
