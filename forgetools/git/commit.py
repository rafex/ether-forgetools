from __future__ import annotations

"""
git/commit.py — Conventional Commits generator with language detection and emoji.

Actions:
    analyze  (default) — analyze staged/unstaged diff and propose a commit message
    commit             — execute git commit with the given --message [--body]
    stage              — run git add . then analyze

Conventional Commits spec: https://www.conventionalcommits.org/
"""

import argparse
import re
from collections import Counter
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "git.commit"

# ── Emoji map ─────────────────────────────────────────────────────────────────

EMOJI: dict[str, str] = {
    "feat":     "✨",
    "fix":      "🐛",
    "docs":     "📝",
    "style":    "🎨",
    "refactor": "♻️",
    "perf":     "⚡",
    "test":     "✅",
    "build":    "📦",
    "ci":       "👷",
    "chore":    "🔧",
    "revert":   "⏪",
}

# ── i18n verb map ─────────────────────────────────────────────────────────────

VERBS: dict[str, dict[str, str]] = {
    "en": {
        "feat":     "add",
        "fix":      "fix",
        "docs":     "update docs",
        "style":    "format code",
        "refactor": "refactor",
        "perf":     "improve performance of",
        "test":     "add tests for",
        "build":    "update build",
        "ci":       "update CI",
        "chore":    "update",
        "revert":   "revert",
    },
    "es": {
        "feat":     "agrega",
        "fix":      "corrige",
        "docs":     "actualiza documentación de",
        "style":    "formatea código de",
        "refactor": "refactoriza",
        "perf":     "mejora rendimiento de",
        "test":     "agrega pruebas para",
        "build":    "actualiza build",
        "ci":       "actualiza CI",
        "chore":    "actualiza",
        "revert":   "revierte",
    },
}

# Spanish keyword hints from git log
_ES_HINTS: set[str] = {
    "agrega", "añade", "corrige", "actualiza", "mejora", "refactoriza",
    "elimina", "mueve", "renombra", "ajusta", "implementa", "arregla",
    "agrego", "agregó", "corrección", "corrije",
}

# ── File-path → type heuristics ───────────────────────────────────────────────

_PATH_RULES: list[tuple[str, str]] = [
    (r"\.github/workflows|\.gitlab-ci|Jenkinsfile|\.circleci|azure-pipelines|\.travis", "ci"),
    (r"pom\.xml|build\.gradle|package\.json|Cargo\.toml|go\.mod|Makefile|Dockerfile|docker-compose", "build"),
    (r"\.(md|rst|adoc|txt)$|^docs/|README", "docs"),
    (r"(^|/)tests?/|__tests__|Test\.java$|Spec\.(js|ts)$|_test\.go$|test_\w+\.py$", "test"),
    (r"\.(css|scss|sass|less)$|\.prettierrc|\.eslintrc", "style"),
    (r"\.editorconfig|\.gitignore|\.gitattributes|\.env\.example", "chore"),
]

# ── Language detection ────────────────────────────────────────────────────────

def _detect_lang(cwd: str | None, forced: str | None) -> str:
    if forced:
        return forced[:2].lower()
    rc, stdout, _ = run_command(["git", "log", "--oneline", "-10"], cwd=cwd)
    if rc != 0 or not stdout.strip():
        return "en"
    words = set(re.findall(r"\b[a-záéíóúüñ]{4,}\b", stdout.lower()))
    return "es" if len(words & _ES_HINTS) >= 2 else "en"


# ── Git diff helpers ──────────────────────────────────────────────────────────

def _file_list(cmd: list[str], cwd: str | None) -> list[str]:
    rc, stdout, _ = run_command(cmd, cwd=cwd)
    return [l.strip() for l in stdout.splitlines() if l.strip()] if rc == 0 else []


def _diff_text(cwd: str | None, staged: bool) -> str:
    flag = "--staged" if staged else ""
    cmd = ["git", "diff"] + ([flag] if flag else []) + ["--no-color"]
    rc, stdout, _ = run_command(cmd, cwd=cwd)
    return stdout if rc == 0 else ""


def _diff_stat(diff: str) -> dict:
    added   = len(re.findall(r"^\+[^+]", diff, re.MULTILINE))
    removed = len(re.findall(r"^-[^-]", diff, re.MULTILINE))
    return {"lines_added": added, "lines_removed": removed}


def _last_sha(cwd: str | None) -> str:
    rc, out, _ = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=cwd)
    return out.strip() if rc == 0 else ""


# ── Type / scope inference ────────────────────────────────────────────────────

def _type_from_paths(files: list[str]) -> str | None:
    for f in files:
        for pattern, ctype in _PATH_RULES:
            if re.search(pattern, f, re.IGNORECASE):
                return ctype
    return None


def _type_from_diff(diff: str) -> str:
    low = diff.lower()
    if any(k in low for k in ("null pointer", "nullpointer", "npe", "exception",
                               "bugfix", "bug fix", "hotfix")):
        return "fix"
    if any(k in low for k in ("@test", "def test_", "describe(", "it(", "#[test]",
                               "@extendwith", "mockito")):
        return "test"
    added   = len(re.findall(r"^\+[^+]", diff, re.MULTILINE))
    removed = len(re.findall(r"^-[^-]", diff, re.MULTILINE))
    if added == 0 and removed == 0:
        return "chore"
    ratio = added / max(removed, 1)
    if ratio > 2.0:
        return "feat"
    if ratio < 0.5:
        return "refactor"
    return "fix" if removed >= added else "feat"


def _scope_from_paths(files: list[str]) -> str | None:
    skip = {"src", "main", "java", "kotlin", "python", "lib", "test",
            "tests", "resources", ".", "", "forgetools"}
    segments: list[str] = []
    for f in files:
        parts = Path(f).parts
        useful = [p for p in parts[:-1] if p.lower() not in skip]
        if useful:
            segments.append(useful[-1])
    if not segments:
        return None
    best, _ = Counter(segments).most_common(1)[0]
    return best if len(best) <= 24 else None


# ── Message builder ───────────────────────────────────────────────────────────

def _auto_summary(files: list[str], ctype: str, lang: str) -> str:
    verb = VERBS.get(lang, VERBS["en"]).get(ctype, "update")
    if not files:
        return f"{verb} changes"
    if len(files) == 1:
        return f"{verb} {Path(files[0]).stem}"
    exts = Counter(Path(f).suffix.lstrip(".") for f in files if Path(f).suffix)
    top = exts.most_common(1)[0][0] if exts else ""
    n = len(files)
    return f"{verb} {n} {top} files" if top else f"{verb} {n} files"


def _build_header(ctype: str, scope: str | None, summary: str,
                  breaking: bool, use_emoji: bool) -> str:
    em = f"{EMOJI.get(ctype, '')} " if use_emoji else ""
    sc = f"({scope})" if scope else ""
    bk = "!" if breaking else ""
    raw = f"{em}{ctype}{sc}{bk}: {summary}"
    # Truncate at 72 chars
    return raw[:71] + "…" if len(raw) > 72 else raw


def _build_body(files: list[str]) -> str | None:
    if len(files) <= 3:
        return None
    listed = "\n".join(f"- {f}" for f in files[:10])
    extra  = f"\n... and {len(files) - 10} more" if len(files) > 10 else ""
    return f"Changed files:\n{listed}{extra}"


def _assemble(header: str, body: str | None, breaking: bool) -> str:
    parts = [header]
    if body:
        parts += ["", body]
    if breaking:
        parts += ["", f"BREAKING CHANGE: see description above"]
    return "\n".join(parts)


# ── Actions ───────────────────────────────────────────────────────────────────

def _do_analyze(cwd: str | None, lang: str, use_emoji: bool) -> dict:
    staged    = _file_list(["git", "diff", "--staged", "--name-only"], cwd)
    unstaged  = _file_list(["git", "diff", "--name-only"], cwd)
    untracked = _file_list(["git", "ls-files", "--others", "--exclude-standard"], cwd)

    has_staged = bool(staged)
    all_empty  = not staged and not unstaged and not untracked

    if all_empty:
        return {
            "status": "nothing_to_commit",
            "message": None,
            "staged": [], "unstaged": [], "untracked": [],
        }

    working = staged if has_staged else (unstaged + untracked)
    diff    = _diff_text(cwd, staged=has_staged)

    ctype    = _type_from_paths(working) or _type_from_diff(diff) or "chore"
    scope    = _scope_from_paths(working)
    summary  = _auto_summary(working, ctype, lang)
    breaking = "breaking change" in diff.lower() or "breaking-change" in diff.lower()
    body     = _build_body(working)
    header   = _build_header(ctype, scope, summary, breaking, use_emoji)
    message  = _assemble(header, body, breaking)

    return {
        "status":      "ready" if has_staged else "unstaged_only",
        "lang":        lang,
        "commit_type": ctype,
        "scope":       scope,
        "summary":     summary,
        "breaking":    breaking,
        "message":     message,
        "staged":      staged,
        "unstaged":    unstaged,
        "untracked":   untracked,
        "has_staged":  has_staged,
        "diff_stat":   _diff_stat(diff),
        "hint": (
            None if has_staged
            else "No staged files — run action=stage or git add before committing"
        ),
    }


def _do_commit(message: str, body: str | None, cwd: str | None) -> dict:
    cmd = ["git", "commit", "-m", message]
    if body:
        cmd += ["-m", body]
    rc, stdout, stderr = run_command(cmd, cwd=cwd)
    return {
        "committed": rc == 0,
        "sha":       _last_sha(cwd) if rc == 0 else None,
        "message":   message,
        "stdout":    stdout.strip(),
        "error":     stderr.strip() if rc != 0 else None,
    }


def _do_stage(cwd: str | None, lang: str, use_emoji: bool) -> dict:
    rc, _, stderr = run_command(["git", "add", "."], cwd=cwd)
    if rc != 0:
        return {"staged_all": False, "error": stderr.strip()}
    data = _do_analyze(cwd, lang, use_emoji)
    data["staged_all"] = True
    return data


# ── Public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action: str = "analyze",
    message: str | None = None,
    body: str | None = None,
    stage_all: bool = False,
    emoji: bool = True,
    lang: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        detected_lang = _detect_lang(cwd, lang)

        effective_action = "stage" if stage_all else action

        if effective_action == "analyze":
            data = _do_analyze(cwd, detected_lang, emoji)

        elif effective_action == "commit":
            if not message:
                return ForgeResult.failure(
                    TOOL,
                    ["--message is required for action=commit"],
                    t.elapsed_ms,
                    suggestion=(
                        "Run action=analyze first to get a proposed message, "
                        "then: action=commit --message '<proposed>'"
                    ),
                )
            data = _do_commit(message, body, cwd)
            if not data["committed"]:
                return ForgeResult.failure(
                    TOOL, [data["error"] or "git commit failed"], t.elapsed_ms,
                    suggestion="Check git status — are there staged changes?",
                )

        elif effective_action == "stage":
            data = _do_stage(cwd, detected_lang, emoji)

        else:
            return ForgeResult.failure(
                TOOL,
                [f"Unknown action '{effective_action}'. Valid: analyze | commit | stage"],
                t.elapsed_ms,
            )

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--action", default="analyze",
        choices=["analyze", "commit", "stage"],
        help=(
            "analyze: inspect diff and propose message (default) | "
            "commit:  execute git commit (requires --message) | "
            "stage:   git add . then analyze"
        ),
    )
    p.add_argument("--message", "-m", default=None,
                   help="Commit message (required for action=commit)")
    p.add_argument("--body",    "-b", default=None,
                   help="Optional commit body paragraph")
    p.add_argument("--stage-all", action="store_true", dest="stage_all",
                   help="Shortcut for action=stage (git add . then analyze)")
    p.add_argument("--no-emoji", action="store_false", dest="emoji",
                   help="Disable emoji prefix")
    p.add_argument("--lang", default=None, choices=["en", "es"],
                   help="Force language for commit message (default: auto-detect)")
    p.add_argument("--cwd", default=None, help="Working directory")


if __name__ == "__main__":
    make_cli(
        TOOL,
        "Conventional Commits generator — analyze diff, propose message, execute commit",
        run,
        _add_args,
    )
