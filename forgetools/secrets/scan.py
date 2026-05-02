"""forgetools.secrets.scan — Scan for secrets in files."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "secrets.scan"

_SKIP_DIRS = {".git", "node_modules", ".venv", "target", "__pycache__", ".tox"}
_SKIP_EXTS = {".class", ".jar", ".pyc", ".so", ".dylib", ".dll", ".exe",
              ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip",
              ".tar", ".gz", ".whl", ".bin"}

_PATTERNS = [
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GENERIC_SECRET", re.compile(
        r"(?i)(api[_-]?key|apikey|secret|token|password)\s*[=:]\s*[\"']?([A-Za-z0-9/+=]{16,})"
    )),
    ("PRIVATE_KEY_HEADER", re.compile(
        r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"
    )),
]


def run(*, path: str = ".", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        base = os.path.join(cwd or ".", path)
        # Try gitleaks first
        findings = _try_gitleaks(base)
        if findings is None:
            # Fallback to regex scan
            findings = _regex_scan(base)

        return ForgeResult.success(TOOL, {
            "clean": len(findings) == 0,
            "findings": findings,
        }, t.elapsed_ms)


def _try_gitleaks(path: str) -> list[dict] | None:
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            report_path = tf.name
        result = subprocess.run(
            ["gitleaks", "detect", "--source", path,
             "--report-format", "json", "--report-path", report_path, "--no-git"],
            capture_output=True, text=True, timeout=60,
        )
        # rc=0 clean, rc=1 leaks found, rc=2 error
        if result.returncode == 2:
            return None
        with open(report_path) as f:
            raw = json.load(f)
        findings = []
        for item in raw or []:
            match_val = item.get("Secret", item.get("Match", ""))
            findings.append({
                "file": item.get("File", ""),
                "line": item.get("StartLine", 0),
                "rule": item.get("RuleID", item.get("Description", "")),
                "match": match_val[:6] + "..." if len(match_val) > 6 else match_val,
            })
        return findings
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return None
    finally:
        try:
            os.unlink(report_path)
        except Exception:
            pass


def _regex_scan(base: str) -> list[dict]:
    findings: list[dict] = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in _SKIP_EXTS:
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        for rule_name, pattern in _PATTERNS:
                            m = pattern.search(line)
                            if m:
                                match_val = m.group(0)
                                findings.append({
                                    "file": fpath,
                                    "line": lineno,
                                    "rule": rule_name,
                                    "match": match_val[:6] + "..." if len(match_val) > 6 else match_val,
                                })
            except (OSError, PermissionError):
                continue
    return findings


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".", help="Path to scan for secrets")


if __name__ == "__main__":
    make_cli(TOOL, "Scan for secrets in files", run, _add_args)
