from __future__ import annotations

"""
test/coverage_report.py — Parse code coverage reports for Java, JavaScript, TypeScript.

Auto-detects format from file content or extension.
Supports:
  JaCoCo XML   — Java  (Maven: target/site/jacoco/jacoco.xml,
                          Gradle: build/reports/jacoco/test/jacocoTestReport.xml)
  Istanbul JSON — JS/TS  (Jest/nyc: coverage/coverage-summary.json)
  lcov.info     — JS/TS  (Jest --coverageReporters=lcov, vitest, c8)

Actions:
    report   (default) — parse coverage file, return full breakdown
    summary            — overall % only (fast check)
    check              — fail if overall line coverage < --min (default 80)
    find               — scan project for coverage files and list them

Common locations scanned with action=find:
  Java:  target/site/jacoco/jacoco.xml
         build/reports/jacoco/**/*.xml
  JS/TS: coverage/coverage-summary.json
         coverage/lcov.info
         .nyc_output/coverage-summary.json
"""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "test.coverage_report"

# ── Common locations ──────────────────────────────────────────────────────────

_JAVA_PATTERNS = [
    "target/site/jacoco/jacoco.xml",
    "build/reports/jacoco/test/jacocoTestReport.xml",
    "build/reports/jacoco/**/*.xml",
    "**/jacoco.xml",
]

_JS_PATTERNS = [
    "coverage/coverage-summary.json",
    ".nyc_output/coverage-summary.json",
    "coverage/lcov.info",
    "lcov.info",
]


def _find_coverage_files(root: Path) -> list[dict]:
    found: list[dict] = []
    for pat in _JAVA_PATTERNS:
        for p in root.glob(pat):
            if p.stat().st_size > 0:
                found.append({"path": str(p.relative_to(root)), "format": "jacoco"})
    for pat in _JS_PATTERNS:
        for p in root.glob(pat):
            if p.stat().st_size > 0:
                fmt = "istanbul" if p.name.endswith(".json") else "lcov"
                found.append({"path": str(p.relative_to(root)), "format": fmt})
    return found


# ── Format detection ──────────────────────────────────────────────────────────

def _detect_format(path: Path) -> str | None:
    if path.suffix == ".xml":
        try:
            head = path.read_text(encoding="utf-8", errors="ignore")[:512]
            if "jacoco" in head.lower() or "<report" in head:
                return "jacoco"
            if "cobertura" in head.lower() or "coverage" in head.lower():
                return "cobertura"
        except OSError:
            pass
        return "jacoco"
    if path.suffix == ".json":
        return "istanbul"
    if path.name in ("lcov.info", "lcov.dat") or path.suffix == ".info":
        return "lcov"
    return None


# ── Unified result shape ──────────────────────────────────────────────────────
# {
#   format: str,
#   language: str,
#   summary: {lines_pct, branches_pct, methods_pct, lines_covered, lines_total},
#   files: [{path, lines_pct, branches_pct, lines_covered, lines_total}]
# }

def _pct(covered: int, total: int) -> float:
    return round(covered / total * 100, 2) if total > 0 else 0.0


# ── JaCoCo XML ────────────────────────────────────────────────────────────────

def _counter(element: ET.Element, ctype: str) -> tuple[int, int]:
    for c in element.findall("counter"):
        if c.get("type") == ctype:
            missed  = int(c.get("missed",  0))
            covered = int(c.get("covered", 0))
            return covered, covered + missed
    return 0, 0


def _parse_jacoco(path: Path) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()

    # Top-level counters
    lc, lt = _counter(root, "LINE")
    bc, bt = _counter(root, "BRANCH")
    mc, mt = _counter(root, "METHOD")

    files: list[dict] = []
    for pkg in root.findall("package"):
        pkg_name = pkg.get("name", "").replace("/", ".")
        for cls in pkg.findall("class"):
            cls_name = cls.get("name", "").replace("/", ".")
            src_file = cls.get("sourcefilename", "")
            flc, flt = _counter(cls, "LINE")
            fbc, fbt = _counter(cls, "BRANCH")
            files.append({
                "path":           f"{pkg_name}/{src_file}" if src_file else cls_name,
                "lines_pct":      _pct(flc, flt),
                "branches_pct":   _pct(fbc, fbt),
                "lines_covered":  flc,
                "lines_total":    flt,
            })

    files.sort(key=lambda f: f["lines_pct"])  # worst first

    return {
        "format":   "jacoco",
        "language": "java",
        "summary": {
            "lines_pct":      _pct(lc, lt),
            "branches_pct":   _pct(bc, bt),
            "methods_pct":    _pct(mc, mt),
            "lines_covered":  lc,
            "lines_total":    lt,
        },
        "files": files,
    }


# ── Istanbul / NYC JSON ───────────────────────────────────────────────────────

def _parse_istanbul(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))

    total    = data.get("total", {})
    lines    = total.get("lines",      {})
    branches = total.get("branches",   {})
    funcs    = total.get("functions",  {})

    files: list[dict] = []
    root = path.parent.parent  # coverage/ → project root (heuristic)

    for fpath, fdata in data.items():
        if fpath == "total":
            continue
        fl  = fdata.get("lines",    {})
        fb  = fdata.get("branches", {})
        display = fpath
        try:
            display = str(Path(fpath).relative_to(root))
        except ValueError:
            pass
        files.append({
            "path":          display,
            "lines_pct":     fl.get("pct", 0),
            "branches_pct":  fb.get("pct", 0),
            "lines_covered": fl.get("covered", 0),
            "lines_total":   fl.get("total", 0),
        })

    files.sort(key=lambda f: f["lines_pct"])

    return {
        "format":   "istanbul",
        "language": "javascript/typescript",
        "summary": {
            "lines_pct":      lines.get("pct", 0),
            "branches_pct":   branches.get("pct", 0),
            "methods_pct":    funcs.get("pct", 0),
            "lines_covered":  lines.get("covered", 0),
            "lines_total":    lines.get("total", 0),
        },
        "files": files,
    }


# ── lcov.info ────────────────────────────────────────────────────────────────

def _parse_lcov(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")

    files: list[dict] = []
    current: dict = {}

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("SF:"):
            current = {"path": line[3:], "lf": 0, "lh": 0, "brda_total": 0, "brda_hit": 0}
        elif line.startswith("LF:"):
            current["lf"] = int(line[3:] or 0)
        elif line.startswith("LH:"):
            current["lh"] = int(line[3:] or 0)
        elif line.startswith("BRF:"):
            current["brda_total"] = int(line[4:] or 0)
        elif line.startswith("BRH:"):
            current["brda_hit"] = int(line[4:] or 0)
        elif line == "end_of_record" and current:
            lf = current["lf"]
            lh = current["lh"]
            bt = current["brda_total"]
            bh = current["brda_hit"]
            files.append({
                "path":          current["path"],
                "lines_pct":     _pct(lh, lf),
                "branches_pct":  _pct(bh, bt),
                "lines_covered": lh,
                "lines_total":   lf,
            })
            current = {}

    if not files:
        return {"format": "lcov", "language": "javascript/typescript",
                "summary": {"lines_pct": 0, "branches_pct": 0, "methods_pct": 0,
                            "lines_covered": 0, "lines_total": 0}, "files": []}

    total_lf = sum(f["lines_total"]   for f in files)
    total_lh = sum(f["lines_covered"] for f in files)
    total_bt = sum(f.get("brda_total", 0) for f in files)  # not stored — recalculate
    total_bh = 0  # not easily summed without re-parsing

    files.sort(key=lambda f: f["lines_pct"])

    return {
        "format":   "lcov",
        "language": "javascript/typescript",
        "summary": {
            "lines_pct":      _pct(total_lh, total_lf),
            "branches_pct":   None,   # not reliably available at aggregate level in lcov
            "methods_pct":    None,
            "lines_covered":  total_lh,
            "lines_total":    total_lf,
        },
        "files": files,
    }


# ── Dispatch ──────────────────────────────────────────────────────────────────

_PARSERS = {
    "jacoco":   _parse_jacoco,
    "istanbul": _parse_istanbul,
    "lcov":     _parse_lcov,
}


def _parse_file(path: Path) -> dict:
    fmt = _detect_format(path)
    if not fmt or fmt not in _PARSERS:
        raise ValueError(f"Unrecognized coverage format for {path.name}")
    return _PARSERS[fmt](path)


# ── run() ─────────────────────────────────────────────────────────────────────

def run(
    *,
    action:  str = "report",
    path:    str | None = None,
    min_pct: float = 80.0,
    worst:   int = 10,
    cwd:     str | None = None,
) -> ForgeResult:
    with Timer() as t:
        base = Path(cwd or ".").resolve()

        if action == "find":
            found = _find_coverage_files(base)
            return ForgeResult.success(TOOL, {
                "found": len(found),
                "files": found,
                "suggestion": (
                    "Pass --path <file> to parse one of these reports"
                    if found else
                    "Run tests with coverage enabled (e.g. mvn test jacoco:report, jest --coverage)"
                ),
            }, t.elapsed_ms)

        # Resolve path
        target: Path | None = None
        if path:
            target = Path(path) if Path(path).is_absolute() else base / path
        else:
            # Auto-find first available report
            found = _find_coverage_files(base)
            if found:
                target = base / found[0]["path"]

        if not target or not target.exists():
            return ForgeResult.failure(
                TOOL,
                ["No coverage report found — pass --path or run action=find"],
                t.elapsed_ms,
                suggestion=(
                    "For Java: mvn test jacoco:report  or  gradle jacocoTestReport\n"
                    "For JS/TS: jest --coverage  or  vitest --coverage  or  c8 npm test"
                ),
            )

        try:
            data = _parse_file(target)
        except Exception as exc:
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)

        summary = data["summary"]
        lines_pct = summary.get("lines_pct") or 0.0

        if action == "summary":
            return ForgeResult.success(TOOL, {
                "format":   data["format"],
                "language": data["language"],
                "summary":  summary,
                "file":     str(target.relative_to(base)),
            }, t.elapsed_ms)

        if action == "check":
            passed = lines_pct >= min_pct
            result_data = {
                "passed":    passed,
                "lines_pct": lines_pct,
                "min_pct":   min_pct,
                "format":    data["format"],
                "language":  data["language"],
            }
            if not passed:
                return ForgeResult(
                    ok=False, tool=TOOL, data=result_data,
                    errors=[f"Coverage {lines_pct:.1f}% is below minimum {min_pct:.0f}%"],
                    duration_ms=t.elapsed_ms,
                )
            return ForgeResult.success(TOOL, result_data, t.elapsed_ms)

        # action == "report"
        # Include only the N worst-covered files for brevity
        all_files = data["files"]
        data["worst_covered"] = all_files[:worst]
        data["total_files"]   = len(all_files)
        data["file"]          = str(target.relative_to(base))
        # Remove full file list to keep response compact
        del data["files"]

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="report",
                   choices=["report", "summary", "check", "find"],
                   help=(
                       "report: full breakdown (default) | "
                       "summary: overall % only | "
                       "check: fail if below --min | "
                       "find: locate coverage files in project"
                   ))
    p.add_argument("--path", default=None,
                   help="Coverage file path (auto-detected if omitted)")
    p.add_argument("--min", dest="min_pct", type=float, default=80.0,
                   help="Minimum line coverage %% for action=check (default: 80)")
    p.add_argument("--worst", type=int, default=10,
                   help="Number of worst-covered files to include in report (default: 10)")
    p.add_argument("--cwd", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Parse code coverage reports (JaCoCo / Istanbul / lcov)", run, _add_args)
