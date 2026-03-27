from __future__ import annotations

"""
java/format.py — Wrapper for google-java-format.

Finds the binary automatically in PATH, Mason (Neovim), opencode, or Homebrew.
Does NOT require any configuration — just works wherever google-java-format is installed.

Actions:
    format  (default) — format files in-place
    check             — exit non-zero if any file would change (CI-safe)
    diff              — show what would change without writing (stdout diff)

Ref: https://github.com/google/google-java-format
"""

import argparse
import glob as _glob
import os
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "java.format"

# ── Binary search order ───────────────────────────────────────────────────────

_SEARCH_PATHS: list[str] = [
    # System PATH (handled separately by shutil.which)
    # Mason (Neovim package manager)
    "~/.local/share/nvim/mason/bin/google-java-format",
    # opencode
    "~/.local/share/opencode/bin/google-java-format",
    # Homebrew Apple Silicon
    "/opt/homebrew/bin/google-java-format",
    # Homebrew Intel
    "/usr/local/bin/google-java-format",
    # Linux common
    "/usr/bin/google-java-format",
    # User tools directory
    "~/tools/google-java-format",
    "~/bin/google-java-format",
]


def _find_binary() -> str | None:
    """Find google-java-format binary. Returns absolute path or None."""
    import shutil

    # 1. Environment variable override
    env_val = os.environ.get("GOOGLE_JAVA_FORMAT")
    if env_val and Path(env_val).is_file():
        return env_val

    # 2. System PATH
    found = shutil.which("google-java-format")
    if found:
        return found

    # 3. Known locations
    for raw in _SEARCH_PATHS:
        p = Path(raw).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)

    # 4. Maven local repo (all-deps jar runnable via java -jar)
    m2 = Path("~/.m2/repository/com/google/googlejavaformat/google-java-format").expanduser()
    if m2.is_dir():
        jars = sorted(m2.rglob("google-java-format-*-all-deps.jar"), reverse=True)
        if jars:
            return f"jar:{jars[0]}"  # special prefix to indicate jar mode

    return None


def _build_cmd(binary: str, files: list[str], style: str,
               action: str, lines: str | None) -> list[str]:
    """Build the google-java-format command."""
    if binary.startswith("jar:"):
        jar_path = binary[4:]
        import shutil
        java = shutil.which("java") or "java"
        cmd = [java, "-jar", jar_path]
    else:
        cmd = [binary]

    # Style
    if style == "aosp":
        cmd += ["--aosp"]

    # Action flags
    if action == "check":
        cmd += ["--dry-run", "--set-exit-if-changed"]
    elif action == "diff":
        pass  # no --replace → stdout only

    if action == "format":
        cmd += ["--replace"]

    # Line range
    if lines:
        cmd += ["--lines", lines]

    cmd += files
    return cmd


def _collect_files(files: list[str] | None, pattern: str | None,
                   cwd: str | None) -> list[str] | str:
    """Return list of .java files to format, or error string."""
    base = Path(cwd or ".").resolve()
    result: list[str] = []

    if files:
        for f in files:
            p = Path(f) if Path(f).is_absolute() else base / f
            if not p.exists():
                return f"File not found: {p}"
            result.append(str(p))

    if pattern:
        matched = _glob.glob(str(base / pattern), recursive=True)
        result.extend(m for m in matched if m.endswith(".java"))

    if not files and not pattern:
        return "Provide --files or --pattern"

    if not result:
        return "No .java files matched"

    return result


# ── run() ─────────────────────────────────────────────────────────────────────

def run(
    *,
    action:  str = "format",
    files:   str | None = None,       # space-separated file paths
    pattern: str | None = None,       # glob, e.g. "src/**/*.java"
    style:   str = "google",          # google | aosp
    lines:   str | None = None,       # e.g. "1:50" for partial format
    binary:  str | None = None,       # override binary path
    cwd:     str | None = None,
) -> ForgeResult:
    with Timer() as t:

        # 1. Find binary
        exe = binary or _find_binary()
        if not exe:
            return ForgeResult.failure(
                TOOL,
                ["google-java-format not found"],
                t.elapsed_ms,
                suggestion=(
                    "Install via Homebrew: brew install google-java-format\n"
                    "Or Mason (Neovim): :MasonInstall google-java-format\n"
                    "Or set GOOGLE_JAVA_FORMAT=/path/to/binary"
                ),
            )

        # 2. Collect files
        file_list_or_err = _collect_files(
            files.split() if files else None,
            pattern,
            cwd,
        )
        if isinstance(file_list_or_err, str):
            return ForgeResult.failure(TOOL, [file_list_or_err], t.elapsed_ms,
                                       suggestion="Pass --files 'A.java B.java' or --pattern 'src/**/*.java'")
        target_files: list[str] = file_list_or_err

        # 3. Validate action
        if action not in ("format", "check", "diff"):
            return ForgeResult.failure(
                TOOL, [f"Unknown action '{action}'. Use: format | check | diff"], t.elapsed_ms
            )

        # 4. Build & run command
        cmd = _build_cmd(exe, target_files, style, action, lines)
        rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=120)

        # 5. Interpret results
        if action == "check":
            # --dry-run prints files that would change; rc=1 means changes needed
            needs_format = [l.strip() for l in stdout.splitlines() if l.strip()]
            return ForgeResult(
                ok=rc == 0,
                tool=TOOL,
                data={
                    "action":         "check",
                    "binary":         exe,
                    "style":          style,
                    "files_checked":  len(target_files),
                    "files_needing_format": needs_format,
                    "formatted":      rc == 0,
                },
                errors=([f"{len(needs_format)} file(s) need formatting"] if rc != 0 else []),
                duration_ms=t.elapsed_ms,
            )

        if action == "diff":
            return ForgeResult.success(TOOL, {
                "action":  "diff",
                "binary":  exe,
                "style":   style,
                "files":   target_files,
                "diff":    stdout,
                "has_changes": bool(stdout.strip()),
            }, t.elapsed_ms)

        # format
        if rc != 0:
            return ForgeResult.failure(
                TOOL, [stderr.strip() or "google-java-format exited non-zero"], t.elapsed_ms,
                suggestion="Check that files are valid Java source"
            )

        return ForgeResult.success(TOOL, {
            "action":          "format",
            "binary":          exe,
            "style":           style,
            "files_formatted": len(target_files),
            "files":           target_files,
        }, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="format", choices=["format", "check", "diff"],
                   help="format: in-place | check: CI mode (exit 1 if changes needed) | diff: show changes")
    p.add_argument("--files", "-f", default=None,
                   help="Space-separated list of .java files")
    p.add_argument("--pattern", default=None,
                   help="Glob pattern relative to cwd, e.g. 'src/**/*.java'")
    p.add_argument("--style", default="google", choices=["google", "aosp"],
                   help="google (2-space, default) or aosp (4-space)")
    p.add_argument("--lines", default=None,
                   help="Format only specific lines, e.g. '1:50'")
    p.add_argument("--binary", default=None,
                   help="Override path to google-java-format binary or jar")
    p.add_argument("--cwd", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Format Java source files with google-java-format", run, _add_args)
