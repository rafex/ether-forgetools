"""
Audit and optionally fix invisible/problematic characters in text files.

Detects:
  - ASCII control chars (NUL, SOH, BEL, ESC, DEL, etc.)
  - UTF-8 BOM at start
  - Embedded Unicode invisibles (ZWSP, ZWNJ, ZWJ, WORD JOINER, FEFF)
  - Tabs (optional, informational)

Modes:
  scan          report only, exit 1 if findings exist
  fix           rewrite files removing problematic chars
  staged        scan only git-staged files (pre-commit use)
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "text.audit_chars"

# ── character tables ──────────────────────────────────────────────────────────

_CTRL_NAMES: dict[int, str] = {
    0x00: "NUL", 0x01: "SOH", 0x02: "STX", 0x03: "ETX", 0x04: "EOT",
    0x05: "ENQ", 0x06: "ACK", 0x07: "BEL", 0x08: "BS",  0x09: "TAB",
    0x0A: "LF",  0x0B: "VT",  0x0C: "FF",  0x0D: "CR",  0x0E: "SO",
    0x0F: "SI",  0x10: "DLE", 0x11: "DC1", 0x12: "DC2", 0x13: "DC3",
    0x14: "DC4", 0x15: "NAK", 0x16: "SYN", 0x17: "ETB", 0x18: "CAN",
    0x19: "EM",  0x1A: "SUB", 0x1B: "ESC", 0x1C: "FS",  0x1D: "GS",
    0x1E: "RS",  0x1F: "US",  0x7F: "DEL",
}

_UNICODE_INVISIBLE: dict[str, str] = {
    "\u200B": "ZERO WIDTH SPACE",
    "\u200C": "ZERO WIDTH NON-JOINER",
    "\u200D": "ZERO WIDTH JOINER",
    "\u2060": "WORD JOINER",
    "\uFEFF": "ZERO WIDTH NO-BREAK SPACE / BOM",
}

# Chars allowed as normal text content (not flagged as control chars)
_ALLOWED_CONTROLS = {0x09, 0x0A, 0x0D}  # TAB, LF, CR

DEFAULT_EXTENSIONS = {".md", ".markdown", ".mdx", ".txt", ".rst", ".adoc"}
DEFAULT_EXCLUDE    = {".git", "node_modules", "dist", "build", "target",
                      ".idea", ".vscode", "__pycache__", ".venv", ".tox"}


# ── core logic ────────────────────────────────────────────────────────────────

def _is_bad_control(ch: str) -> bool:
    code = ord(ch)
    return (code == 0x7F) or (0x00 <= code <= 0x1F and code not in _ALLOWED_CONTROLS)


def _describe(ch: str) -> str:
    code = ord(ch)
    if ch in _UNICODE_INVISIBLE:
        return f"U+{code:04X} {_UNICODE_INVISIBLE[ch]}"
    if code in _CTRL_NAMES:
        return f"0x{code:02X} {_CTRL_NAMES[code]}"
    return f"U+{code:04X}"


def _line_col(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    last_nl = text.rfind("\n", 0, offset)
    col = offset + 1 if last_nl == -1 else offset - last_nl
    return line, col


def _scan(text: str, report_tabs: bool) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    if text.startswith("\uFEFF"):
        findings.append({"offset": 0, "line": 1, "col": 1,
                         "char": "\uFEFF", "hex": "U+FEFF",
                         "description": "UTF-8 BOM at start of file",
                         "kind": "bom"})

    for idx, ch in enumerate(text):
        if idx == 0 and ch == "\uFEFF":
            continue  # already reported above

        if ch in _UNICODE_INVISIBLE:
            line, col = _line_col(text, idx)
            findings.append({"offset": idx, "line": line, "col": col,
                              "char": repr(ch), "hex": f"U+{ord(ch):04X}",
                              "description": _describe(ch),
                              "kind": "unicode_invisible"})

        elif _is_bad_control(ch):
            line, col = _line_col(text, idx)
            findings.append({"offset": idx, "line": line, "col": col,
                              "char": repr(ch), "hex": f"0x{ord(ch):02X}",
                              "description": _describe(ch),
                              "kind": "control_char"})

        elif report_tabs and ch == "\t":
            line, col = _line_col(text, idx)
            findings.append({"offset": idx, "line": line, "col": col,
                              "char": repr(ch), "hex": "0x09",
                              "description": "TAB",
                              "kind": "tab"})

    return findings


def _fix(text: str) -> str:
    out: list[str] = []
    for idx, ch in enumerate(text):
        if idx == 0 and ch == "\uFEFF":
            continue
        if ch in _UNICODE_INVISIBLE:
            continue
        if _is_bad_control(ch):
            continue
        out.append(ch)
    return "".join(out)


# ── file iteration ────────────────────────────────────────────────────────────

def _should_skip(path: Path, excluded: set[str]) -> bool:
    return any(part in excluded for part in path.parts)


def _iter_files(root: Path, extensions: set[str], excluded: set[str]):
    for p in root.rglob("*"):
        if p.is_file() and not _should_skip(p, excluded) and p.suffix.lower() in extensions:
            yield p


def _staged_files(root: Path, extensions: set[str]) -> list[Path]:
    """Return git-staged files matching extensions."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return []
        return [
            root / f for f in result.stdout.splitlines()
            if Path(f).suffix.lower() in extensions and (root / f).exists()
        ]
    except Exception:
        return []


# ── public API ────────────────────────────────────────────────────────────────

def run(
    *,
    root: str = ".",
    fix: bool = False,
    staged: bool = False,
    extensions: str = ".md,.markdown,.mdx,.txt,.rst",
    exclude: str = ".git,node_modules,dist,build,target,__pycache__,.venv",
    report_tabs: bool = False,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        base = Path(cwd or ".").resolve()
        scan_root = (base / root).resolve() if root != "." else base

        if not scan_root.exists():
            return ForgeResult.failure(TOOL, [f"Path not found: {scan_root}"], t.elapsed_ms)

        exts = {(e.strip() if e.strip().startswith(".") else f".{e.strip()}").lower()
                for e in extensions.split(",")}
        excl = {e.strip() for e in exclude.split(",")}

        if staged:
            files = _staged_files(scan_root, exts)
        else:
            files = list(_iter_files(scan_root, exts, excl))

        file_results: list[dict[str, Any]] = []
        total_findings = 0
        fixed_files = 0

        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                file_results.append({"path": str(path.relative_to(scan_root)),
                                     "error": str(e), "findings": [], "fixed": False})
                continue

            findings = _scan(text, report_tabs)
            fixed = False

            if fix and findings:
                cleaned = _fix(text)
                if cleaned != text:
                    try:
                        path.write_text(cleaned, encoding="utf-8", newline="")
                        fixed = True
                        fixed_files += 1
                    except Exception as e:
                        findings.append({"kind": "write_error", "description": str(e)})

            total_findings += len(findings)
            if findings:
                file_results.append({
                    "path": str(path.relative_to(scan_root)),
                    "findings": findings,
                    "fixed": fixed,
                })

        data: dict[str, Any] = {
            "root":               str(scan_root),
            "mode":               "staged" if staged else ("fix" if fix else "scan"),
            "total_files":        len(files),
            "files_with_issues":  len(file_results),
            "total_findings":     total_findings,
            "fixed_files":        fixed_files,
            "files":              file_results,
        }

        # ok=False when there are findings (useful for CI: exit 1)
        if total_findings > 0 and not fix:
            return ForgeResult(
                ok=False, tool=TOOL, data=data,
                errors=[f"{total_findings} invisible/problematic character(s) found in "
                        f"{len(file_results)} file(s)"],
                duration_ms=t.elapsed_ms,
                suggestion="Re-run with --fix to remove them automatically",
            )

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("root", nargs="?", default=".",
                   help="Root path to scan (default: current dir)")
    p.add_argument("--fix", action="store_true",
                   help="Rewrite files removing problematic characters")
    p.add_argument("--staged", action="store_true",
                   help="Scan only git-staged files (pre-commit mode)")
    p.add_argument("--extensions", default=".md,.markdown,.mdx,.txt,.rst",
                   help="Comma-separated extensions to scan")
    p.add_argument("--exclude", default=".git,node_modules,dist,build,target,__pycache__,.venv",
                   help="Comma-separated directory names to skip")
    p.add_argument("--report-tabs", dest="report_tabs", action="store_true",
                   help="Also report TAB characters (informational)")


if __name__ == "__main__":
    make_cli(TOOL, "Audit invisible/problematic characters in text files", run, _add_args)
