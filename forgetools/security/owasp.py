from __future__ import annotations

"""
security/owasp.py — OWASP Dependency-Check wrapper.

Finds the dependency-check binary and runs a vulnerability scan, or parses
an existing JSON/XML report without re-running the scan.

Checks third-party dependencies (JARs, node_modules, etc.) against the
NVD (National Vulnerability Database) for known CVEs — this is OWASP's
Dependency-Check tool, NOT a static code analysis tool.

For static code OWASP Top 10 analysis, pair this with:
  - SpotBugs + Find Security Bugs plugin  (Java)
  - ESLint security plugin                (JS/TS)
  - Semgrep with owasp ruleset            (multi-language)

Actions:
    scan    — run dependency-check and return structured vulnerabilities
    report  — parse an existing dependency-check JSON report (no re-scan)
    find    — locate dependency-check binary and any existing reports

Binary search order:
  1. DEPENDENCY_CHECK env var
  2. dependency-check / dependency-check.sh in PATH
  3. ~/.local/share/dependency-check/bin/
  4. ~/tools/dependency-check/bin/
  5. /opt/dependency-check/bin/
  6. Homebrew: /opt/homebrew/opt/dependency-check/bin/

Ref: https://owasp.org/www-project-dependency-check/
     https://github.com/jeremylong/DependencyCheck
"""

import argparse
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "security.owasp"

VERSION = "11.1.1"  # bundled version reference

# ── Binary search ─────────────────────────────────────────────────────────────

_BINARY_NAMES = ["dependency-check", "dependency-check.sh", "dependency-check.bat"]

_SEARCH_DIRS: list[str] = [
    "~/.local/share/dependency-check/bin",
    "~/tools/dependency-check/bin",
    "/opt/dependency-check/bin",
    "/opt/homebrew/opt/dependency-check/bin",
    "/usr/local/bin",
    "/usr/bin",
]

_REPORT_PATTERNS = [
    "dependency-check-report.json",
    "target/dependency-check-report.json",
    "build/reports/dependency-check-report.json",
    "**/dependency-check-report.json",
]


def _find_binary() -> str | None:
    import shutil

    env = os.environ.get("DEPENDENCY_CHECK")
    if env and Path(env).is_file():
        return env

    for name in _BINARY_NAMES:
        found = shutil.which(name)
        if found:
            return found

    for raw_dir in _SEARCH_DIRS:
        d = Path(raw_dir).expanduser()
        if d.is_dir():
            for name in _BINARY_NAMES:
                p = d / name
                if p.is_file() and os.access(p, os.X_OK):
                    return str(p)

    return None


def _find_reports(root: Path) -> list[str]:
    found: list[str] = []
    for pat in _REPORT_PATTERNS:
        for p in root.glob(pat):
            if p.stat().st_size > 0:
                found.append(str(p.relative_to(root)))
    return found


# ── Severity helpers ──────────────────────────────────────────────────────────

_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4, "NONE": 5}


def _severity_label(cvss_score: float | None, severity: str | None) -> str:
    if severity:
        return severity.upper()
    if cvss_score is None:
        return "NONE"
    if cvss_score >= 9.0:
        return "CRITICAL"
    if cvss_score >= 7.0:
        return "HIGH"
    if cvss_score >= 4.0:
        return "MEDIUM"
    if cvss_score > 0:
        return "LOW"
    return "NONE"


# ── JSON report parser ────────────────────────────────────────────────────────

def _parse_json_report(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))

    scan_info = data.get("projectInfo", {})
    vulns: list[dict] = []

    for dep in data.get("dependencies", []):
        dep_name = dep.get("fileName", dep.get("filePath", "unknown"))
        packages = dep.get("packages", [])
        pkg_id = packages[0].get("id", dep_name) if packages else dep_name

        for vuln in dep.get("vulnerabilities", []):
            name     = vuln.get("name", "")
            severity = vuln.get("severity", "").upper()
            cvssv3   = vuln.get("cvssv3", {}) or {}
            cvssv2   = vuln.get("cvssv2", {}) or {}
            score    = cvssv3.get("baseScore") or cvssv2.get("score")
            severity = _severity_label(score, severity or None)

            cwe_list = [c.get("cweId", "") for c in vuln.get("cwes", [])]

            vulns.append({
                "cve":         name,
                "severity":    severity,
                "cvss_score":  score,
                "package":     pkg_id,
                "file":        dep_name,
                "cwe":         cwe_list,
                "description": vuln.get("description", "")[:300],
                "references":  [r.get("url") for r in vuln.get("references", [])[:3]],
            })

    vulns.sort(key=lambda v: _SEVERITY_ORDER.get(v["severity"], 9))

    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    for v in vulns:
        counts[v["severity"]] = counts.get(v["severity"], 0) + 1

    return {
        "scan_date":   scan_info.get("reportDate", ""),
        "project":     scan_info.get("name", ""),
        "total":       len(vulns),
        "by_severity": counts,
        "has_critical": counts["CRITICAL"] > 0,
        "has_high":     counts["HIGH"] > 0,
        "vulnerabilities": vulns,
    }


# ── XML report parser (fallback) ──────────────────────────────────────────────

def _parse_xml_report(path: Path) -> dict:
    ns = {"dc": "https://jeremylong.github.io/DependencyCheck/dependency-check.1.3.xsd"}
    tree = ET.parse(path)
    root = tree.getroot()

    vulns: list[dict] = []
    for dep in root.findall(".//dc:dependency", ns):
        fname = dep.findtext("dc:fileName", "", ns)
        for vuln in dep.findall(".//dc:vulnerability", ns):
            name  = vuln.findtext("dc:name", "", ns)
            sev   = vuln.findtext("dc:severity", "", ns).upper()
            score_text = vuln.findtext(".//dc:baseScore", None, ns)
            score = float(score_text) if score_text else None
            desc  = vuln.findtext("dc:description", "", ns)[:300]
            vulns.append({
                "cve": name, "severity": _severity_label(score, sev or None),
                "cvss_score": score, "package": fname, "file": fname,
                "cwe": [], "description": desc, "references": [],
            })

    vulns.sort(key=lambda v: _SEVERITY_ORDER.get(v["severity"], 9))
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for v in vulns:
        counts[v["severity"]] = counts.get(v["severity"], 0) + 1

    return {
        "scan_date": "", "project": "", "total": len(vulns),
        "by_severity": counts,
        "has_critical": counts.get("CRITICAL", 0) > 0,
        "has_high":     counts.get("HIGH", 0) > 0,
        "vulnerabilities": vulns,
    }


def _parse_report(path: Path) -> dict:
    if path.suffix == ".json":
        return _parse_json_report(path)
    if path.suffix == ".xml":
        return _parse_xml_report(path)
    raise ValueError(f"Unsupported report format: {path.suffix} (use .json or .xml)")


# ── run() ─────────────────────────────────────────────────────────────────────

def run(
    *,
    action:    str = "scan",
    scan_path: str = ".",
    report:    str | None = None,
    format:    str = "JSON",
    out_dir:   str = ".",
    severity:  str | None = None,   # filter: CRITICAL, HIGH, MEDIUM, LOW
    binary:    str | None = None,
    cwd:       str | None = None,
) -> ForgeResult:
    with Timer() as t:
        base = Path(cwd or ".").resolve()

        # ── find ──────────────────────────────────────────────────────────
        if action == "find":
            exe = binary or _find_binary()
            reports = _find_reports(base)
            return ForgeResult.success(TOOL, {
                "binary":          exe,
                "binary_found":    exe is not None,
                "existing_reports": reports,
                "install_hint": (
                    None if exe else
                    "Install via Homebrew: brew install dependency-check\n"
                    "Or download: https://github.com/jeremylong/DependencyCheck/releases"
                ),
            }, t.elapsed_ms)

        # ── report (parse existing) ───────────────────────────────────────
        if action == "report":
            target: Path | None = None
            if report:
                target = Path(report) if Path(report).is_absolute() else base / report
            else:
                existing = _find_reports(base)
                if existing:
                    target = base / existing[0]

            if not target or not target.exists():
                return ForgeResult.failure(
                    TOOL,
                    ["No dependency-check report found"],
                    t.elapsed_ms,
                    suggestion="Run action=scan first, or pass --report path/to/dependency-check-report.json",
                )
            try:
                data = _parse_report(target)
            except Exception as exc:
                return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)

            data["report_file"] = str(target.relative_to(base))
            if severity:
                data["vulnerabilities"] = [
                    v for v in data["vulnerabilities"]
                    if v["severity"] == severity.upper()
                ]
            return ForgeResult(
                ok=not data["has_critical"] and not data["has_high"],
                tool=TOOL,
                data=data,
                errors=(
                    [f"{data['by_severity'].get('CRITICAL',0)} critical, "
                     f"{data['by_severity'].get('HIGH',0)} high vulnerabilities found"]
                    if data["has_critical"] or data["has_high"] else []
                ),
                duration_ms=t.elapsed_ms,
            )

        # ── scan ──────────────────────────────────────────────────────────
        if action == "scan":
            exe = binary or _find_binary()
            if not exe:
                return ForgeResult.failure(
                    TOOL,
                    ["dependency-check binary not found"],
                    t.elapsed_ms,
                    suggestion=(
                        "Install via Homebrew: brew install dependency-check\n"
                        "Or download from: https://github.com/jeremylong/DependencyCheck/releases\n"
                        "Or set env var: export DEPENDENCY_CHECK=/path/to/dependency-check"
                    ),
                )

            scan_dir   = Path(scan_path) if Path(scan_path).is_absolute() else base / scan_path
            output_dir = Path(out_dir)   if Path(out_dir).is_absolute()   else base / out_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            report_fmt  = format.upper()
            report_name = f"dependency-check-report.{report_fmt.lower()}"
            report_path = output_dir / report_name

            cmd = [
                exe,
                "--scan",     str(scan_dir),
                "--format",   report_fmt,
                "--out",      str(output_dir),
                "--project",  scan_dir.name,
            ]

            rc, stdout, stderr = run_command(cmd, cwd=str(base), timeout=600)
            if rc != 0 and not report_path.exists():
                return ForgeResult.failure(
                    TOOL,
                    [stderr.strip() or f"dependency-check exited with code {rc}"],
                    t.elapsed_ms,
                    suggestion="Check NVD connectivity — first run downloads the vulnerability database (~500MB)",
                )

            # Parse the generated report
            if report_path.exists():
                try:
                    data = _parse_report(report_path)
                    data["report_file"] = str(report_path.relative_to(base))
                    if severity:
                        data["vulnerabilities"] = [
                            v for v in data["vulnerabilities"]
                            if v["severity"] == severity.upper()
                        ]
                    return ForgeResult(
                        ok=not data["has_critical"] and not data["has_high"],
                        tool=TOOL,
                        data=data,
                        errors=(
                            [f"{data['by_severity'].get('CRITICAL',0)} critical, "
                             f"{data['by_severity'].get('HIGH',0)} high vulnerabilities found"]
                            if data["has_critical"] or data["has_high"] else []
                        ),
                        duration_ms=t.elapsed_ms,
                    )
                except Exception as exc:
                    return ForgeResult.failure(TOOL, [f"Report parse error: {exc}"], t.elapsed_ms)

            return ForgeResult.success(TOOL, {
                "scanned":     str(scan_dir),
                "report_file": str(report_path),
                "stdout":      stdout[:2000],
            }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: scan | report | find"],
            t.elapsed_ms,
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="scan",
                   choices=["scan", "report", "find"],
                   help=(
                       "scan: run dependency-check and parse result (default) | "
                       "report: parse existing JSON/XML report | "
                       "find: locate binary and existing reports"
                   ))
    p.add_argument("--scan-path", dest="scan_path", default=".",
                   help="Directory to scan (default: .)")
    p.add_argument("--report", default=None,
                   help="Path to existing report (for action=report)")
    p.add_argument("--format", default="JSON", choices=["JSON", "XML", "HTML", "CSV"],
                   help="Report format for action=scan (default: JSON)")
    p.add_argument("--out-dir", dest="out_dir", default=".",
                   help="Output directory for generated report (default: .)")
    p.add_argument("--severity", default=None,
                   choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                   help="Filter vulnerabilities by minimum severity")
    p.add_argument("--binary", default=None,
                   help="Override dependency-check binary path")
    p.add_argument("--cwd", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "OWASP Dependency-Check — scan dependencies for CVEs", run, _add_args)
