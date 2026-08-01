from __future__ import annotations

"""
fs/find_by_type.py — Find files by language/type across a directory tree.

Supported types: markdown, sql, java, python, javascript, css, html,
                 shell, bash, php, rust, go, toml, yaml, json, log, txt, zip

Usage:
    forge fs find-by-type --type java --path src/
    forge fs find-by-type --type python --path . --max 50
    forge fs find-by-type --type yaml --path . --no-recursive
"""

import argparse
import os
import shutil
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "fs.find_by_type"

# ── Type → extensions map ──────────────────────────────────────────────────────

TYPE_MAP: dict[str, list[str]] = {
    "markdown":   [".md", ".mdx", ".markdown"],
    "sql":        [".sql"],
    "java":       [".java"],
    "python":     [".py", ".pyw", ".pyi"],
    "javascript": [".js", ".mjs", ".cjs", ".jsx"],
    "typescript": [".ts", ".tsx"],
    "css":        [".css", ".scss", ".sass", ".less"],
    "html":       [".html", ".htm", ".xhtml"],
    "shell":      [".sh", ".bash", ".zsh", ".fish", ".ksh"],
    "bash":       [".sh", ".bash"],
    "php":        [".php", ".phtml", ".php3", ".php4", ".php5"],
    "rust":       [".rs"],
    "go":         [".go"],
    "toml":       [".toml"],
    "yaml":       [".yml", ".yaml"],
    "json":       [".json", ".jsonc", ".json5"],
    "log":        [".log"],
    "txt":        [".txt"],
    "zip":        [".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2",
                   ".tar.xz", ".gz", ".bz2", ".xz", ".7z", ".rar"],
    "xml":        [".xml", ".xsd", ".xsl", ".xslt"],
    "kotlin":     [".kt", ".kts"],
    "swift":      [".swift"],
    "ruby":       [".rb"],
    "c":          [".c", ".h"],
    "cpp":        [".cpp", ".cc", ".cxx", ".hpp", ".hxx"],
    "dockerfile": ["Dockerfile"],
    "makefile":   ["Makefile", "makefile", ".mk"],
}

IGNORE_DIRS: set[str] = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    "target", "dist", "build", ".next", ".cache", "vendor",
    ".idea", ".vscode", ".tox", ".eggs",
}


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} TB"


def run(
    *,
    type: str,
    path: str = ".",
    recursive: bool = True,
    max: int = 200,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        ftype = type.lower()
        if ftype not in TYPE_MAP:
            known = sorted(TYPE_MAP.keys())
            return ForgeResult.failure(
                TOOL,
                [f"Unknown type '{ftype}'"],
                t.elapsed_ms,
                suggestion=f"Valid types: {', '.join(known)}",
            )

        extensions = set(TYPE_MAP[ftype])
        base = Path(cwd or ".").resolve()
        root = Path(path) if Path(path).is_absolute() else base / path

        if not root.exists():
            return ForgeResult.failure(
                TOOL, [f"Path not found: {root}"], t.elapsed_ms,
            )

        if shutil.which("fd"):
            fast_result = _run_fd(root, base, ftype, extensions, recursive, max, t)
            if fast_result is not None:
                return fast_result

        found: list[dict] = []

        if recursive:
            walker = os.walk(root)
        else:
            walker = [(str(root), [], [f.name for f in root.iterdir() if f.is_file()])]  # type: ignore[assignment]

        for dirpath, dirnames, filenames in walker:
            if recursive:
                dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            for fname in filenames:
                fp = Path(dirpath) / fname
                match = (
                    fp.suffix.lower() in extensions
                    or fp.name in extensions  # Dockerfile, Makefile
                )
                if not match:
                    continue
                try:
                    stat = fp.stat()
                    found.append({
                        "path":     str(fp.relative_to(base)),
                        "size":     stat.st_size,
                        "size_hr":  _human_size(stat.st_size),
                        "modified": int(stat.st_mtime),
                    })
                except OSError:
                    found.append({"path": str(fp.relative_to(base)), "size": 0, "size_hr": "?", "modified": 0})

                if len(found) >= max:
                    break
            if len(found) >= max:
                break

        found.sort(key=lambda x: x["path"])

        return ForgeResult.success(TOOL, {
            "type":        ftype,
            "extensions":  sorted(extensions),
            "root":        str(root),
            "recursive":   recursive,
            "count":       len(found),
            "truncated":   len(found) >= max,
            "files":       found,
            "backend":     "python",
        }, t.elapsed_ms)


def _run_fd(
    root: Path,
    base: Path,
    type_name: str,
    extensions: set[str],
    recursive: bool,
    limit: int,
    timer: Timer,
) -> ForgeResult | None:
    cmd = ["fd", "--type", "file", "--hidden", "--no-ignore-vcs", "--print0"]
    if not recursive:
        cmd += ["--max-depth", "1"]
    for excluded in sorted(IGNORE_DIRS):
        cmd += ["--exclude", excluded]
    cmd += ["", str(root)]
    try:
        rc, stdout, stderr = run_command(cmd, timeout=60)
    except (FileNotFoundError, OSError):
        return None
    if rc != 0:
        return ForgeResult.failure(
            TOOL,
            [stderr.strip() or f"fd exited with code {rc}"],
            timer.elapsed_ms,
            suggestion="Install fd or retry with the Python fallback",
        )

    found: list[dict] = []
    for raw in stdout.split("\0"):
        if not raw:
            continue
        fp = Path(raw)
        if fp.suffix.lower() not in extensions and fp.name not in extensions:
            continue
        try:
            stat = fp.stat()
            found.append({
                "path": str(fp.relative_to(base)),
                "size": stat.st_size,
                "size_hr": _human_size(stat.st_size),
                "modified": int(stat.st_mtime),
            })
        except OSError:
            continue
        if limit > 0 and len(found) >= limit:
            break
    found.sort(key=lambda item: item["path"])
    return ForgeResult.success(TOOL, {
        "type": type_name,
        "extensions": sorted(extensions),
        "root": str(root),
        "recursive": recursive,
        "count": len(found),
        "truncated": limit > 0 and len(found) >= limit,
        "files": found,
        "backend": "fd",
    }, timer.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--type",  required=True,
                   help=f"File type to search. One of: {', '.join(sorted(TYPE_MAP))}")
    p.add_argument("--path",  default=".", help="Root directory to search (default: .)")
    p.add_argument("--max",   type=int, default=200, help="Max results (default: 200)")
    p.add_argument("--no-recursive", action="store_false", dest="recursive",
                   help="Disable recursive search")
    p.add_argument("--cwd",   default=None, help="Working directory")


if __name__ == "__main__":
    make_cli(TOOL, "Find files by language/type", run, _add_args)
