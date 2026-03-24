from __future__ import annotations

"""
context/repo_size.py — Clasifica el tamaño de un repositorio git.

Adaptado al patrón ForgeResult desde repo-size.py (standalone).

Clasificación:
    PEQUEÑO  → < 5k LOC  y < 50  archivos
    MEDIANO  → < 20k LOC y < 200 archivos
    GRANDE   → < 80k LOC y < 800 archivos
    GIGANTE  → ≥ 80k LOC o ≥ 800 archivos
"""

import argparse
import os
import time
from collections import defaultdict
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "context.repo_size"

# ── Extensiones ───────────────────────────────────────────────────────────────

LANG_EXTENSIONS: dict[str, list[str]] = {
    "Java":       [".java"],
    "JavaScript": [".js", ".mjs", ".cjs"],
    "TypeScript": [".ts", ".tsx"],
    "Python":     [".py"],
    "PHP":        [".php"],
    "Rust":       [".rs"],
    "Shell":      [".sh", ".bash", ".zsh"],
    "CSS":        [".css", ".scss", ".sass", ".less"],
    "HTML":       [".html", ".htm"],
    "XML":        [".xml"],
    "YAML":       [".yml", ".yaml"],
    "JSON":       [".json"],
    "Markdown":   [".md", ".mdx"],
    "SQL":        [".sql"],
    "Go":         [".go"],
    "C":          [".c", ".h"],
    "C++":        [".cpp", ".cc", ".cxx", ".hpp"],
    "Ruby":       [".rb"],
    "Kotlin":     [".kt", ".kts"],
    "Swift":      [".swift"],
}

_EXT_MAP: dict[str, str] = {
    ext: lang
    for lang, exts in LANG_EXTENSIONS.items()
    for ext in exts
}

IGNORE_DIRS: set[str] = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    "target", ".mvn", "dist", "build", ".next", ".nuxt", "out",
    "coverage", ".cache", "vendor", ".idea", ".vscode",
    ".eggs", ".tox",
}

# ── Umbrales ──────────────────────────────────────────────────────────────────

THRESHOLDS: list[tuple[str, int | None, int | None, str]] = [
    ("PEQUEÑO",  5_000,   50,   "< 5k LOC  /  < 50 archivos"),
    ("MEDIANO",  20_000,  200,  "< 20k LOC /  < 200 archivos"),
    ("GRANDE",   80_000,  800,  "< 80k LOC /  < 800 archivos"),
    ("GIGANTE",  None,    None, "≥ 80k LOC o  ≥ 800 archivos"),
]

REVIEW_STEPS: dict[str, int] = {
    "PEQUEÑO": 12,
    "MEDIANO": 20,
    "GRANDE":  28,
    "GIGANTE": 40,
}

# ── Helpers internos ──────────────────────────────────────────────────────────

def _git_root(path: Path) -> Path | None:
    rc, stdout, _ = run_command(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(path),
    )
    return Path(stdout.strip()) if rc == 0 and stdout.strip() else None


def _git_int(cmd: list[str], root: Path) -> int:
    rc, stdout, _ = run_command(cmd, cwd=str(root))
    try:
        return int(stdout.strip()) if rc == 0 else 0
    except ValueError:
        return 0


def _git_meta(root: Path) -> dict:
    commits = _git_int(["git", "rev-list", "--count", "HEAD"], root)

    rc, stdout, _ = run_command(
        ["git", "shortlog", "-sn", "--no-merges", "HEAD"],
        cwd=str(root),
    )
    contributors = len([l for l in stdout.splitlines() if l.strip()]) if rc == 0 else 0

    rc, stdout, _ = run_command(
        ["git", "branch", "-a"], cwd=str(root),
    )
    branches = len([l for l in stdout.splitlines() if l.strip()]) if rc == 0 else 0

    age_days = 0
    rc, stdout, _ = run_command(
        ["git", "log", "--reverse", "--format=%at", "--max-count=1"],
        cwd=str(root),
    )
    if rc == 0 and stdout.strip():
        try:
            age_days = int((time.time() - int(stdout.strip())) / 86400)
        except ValueError:
            pass

    # disk size excluding .git
    total_bytes = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            try:
                total_bytes += (Path(dirpath) / f).stat().st_size
            except OSError:
                pass
    disk_mb = round(total_bytes / (1024 * 1024), 2)

    return {
        "commits":      commits,
        "contributors": contributors,
        "branches":     branches,
        "age_days":     age_days,
        "disk_mb":      disk_mb,
    }


def _scan(root: Path) -> dict:
    lang_files: dict[str, int] = defaultdict(int)
    lang_lines: dict[str, int] = defaultdict(int)
    total_files = total_lines = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            fp = Path(dirpath) / fname
            lang = _EXT_MAP.get(fp.suffix.lower(), "Otro")
            try:
                with open(fp, encoding="utf-8", errors="ignore") as fh:
                    lines = sum(1 for _ in fh)
            except OSError:
                lines = 0
            total_files += 1
            total_lines += lines
            lang_files[lang] += 1
            lang_lines[lang] += lines

    by_lang = {
        lang: {"files": lang_files[lang], "lines": lang_lines[lang]}
        for lang in sorted(lang_lines, key=lambda x: -lang_lines[x])
    }
    return {"total_files": total_files, "total_lines": total_lines, "by_lang": by_lang}


def _classify(total_files: int, total_lines: int) -> str:
    for label, max_lines, max_files, _ in THRESHOLDS:
        if max_lines is None:
            return label
        if total_lines < max_lines and total_files < max_files:
            return label
    return "GIGANTE"


# ── Función principal ─────────────────────────────────────────────────────────

def run(*, path: str = ".", show_steps: bool = False, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        target = Path(path).resolve()
        if not target.exists():
            return ForgeResult.failure(
                TOOL,
                [f"Path does not exist: {target}"],
                t.elapsed_ms,
                suggestion="Provide a valid directory path",
            )

        root = _git_root(target) or target
        is_git = _git_root(target) is not None

        scan = _scan(root)
        git = _git_meta(root) if is_git else {}
        size_label = _classify(scan["total_files"], scan["total_lines"])

        thresholds_info = [
            {"label": lbl, "max_lines": ml, "max_files": mf, "description": desc}
            for lbl, ml, mf, desc in THRESHOLDS
        ]

        data: dict = {
            "repo":           str(root),
            "name":           root.name,
            "is_git":         is_git,
            "classification": size_label,
            "total_files":    scan["total_files"],
            "total_lines":    scan["total_lines"],
            "by_lang":        scan["by_lang"],
            "git":            git,
            "thresholds":     thresholds_info,
        }

        if show_steps:
            data["review_steps"] = REVIEW_STEPS[size_label]

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path",       default=".", help="Path to the repository (default: .)")
    p.add_argument("--show-steps", action="store_true", dest="show_steps",
                   help="Include recommended steps count for @review agent")


if __name__ == "__main__":
    make_cli(TOOL, "Classify repository size and language breakdown", run, _add_args)
