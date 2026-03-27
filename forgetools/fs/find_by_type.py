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
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

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
        }, t.elapsed_ms)


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
