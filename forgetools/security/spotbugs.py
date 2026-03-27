from __future__ import annotations

"""
security/spotbugs.py — SpotBugs + Find Security Bugs (Java static security analysis).

Finds security vulnerabilities in Java bytecode using SpotBugs with the
Find Security Bugs plugin. Covers OWASP Top 10 issues:
  - SQL Injection, XSS, Path Traversal, LDAP/XPath/Command Injection
  - Weak cryptography (MD5, SHA1, DES), hardcoded credentials
  - Predictable random, unsafe deserialization, SSRF, open redirect

Run strategies (first available):
  1. Maven plugin:  mvn com.github.spotbugs:spotbugs-maven-plugin:spotbugs
  2. Gradle plugin: gradle spotbugsMain
  3. Standalone JAR via java -jar (requires spotbugs + findsecbugs JARs)
  4. action=report — parse an existing SpotBugsXml.xml without re-running

Actions:
    scan    — run spotbugs and parse the XML report
    report  — parse an existing SpotBugsXml.xml / spotbugs.xml
    find    — locate binary/JARs and existing reports

Security categories detected by Find Security Bugs:
  SQL_INJECTION, XSS_*, PATH_TRAVERSAL_*, LDAP_INJECTION,
  XPATH_INJECTION, COMMAND_INJECTION, HARD_CODE_PASSWORD,
  HARD_CODE_KEY, WEAK_MESSAGE_DIGEST_*, PREDICTABLE_RANDOM,
  UNVALIDATED_REDIRECT, XXE_*, SSRF, DESERIALIZATION_GADGET

Ref: https://spotbugs.github.io/
     https://find-sec-bugs.github.io/
"""

import argparse
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "security.spotbugs"

# ── Security-relevant SpotBugs categories and bug types ───────────────────────

SECURITY_CATEGORIES = {"SECURITY", "MALICIOUS_CODE"}

SECURITY_BUG_PREFIXES = (
    "SQL_", "XSS_", "PATH_TRAVERSAL", "LDAP_", "XPATH_", "COMMAND_",
    "HARD_CODE", "WEAK_MESSAGE_DIGEST", "WEAK_TRUST", "PREDICTABLE_RANDOM",
    "UNVALIDATED_REDIRECT", "XXE_", "SSRF", "DESERIALIZATION_GADGET",
    "INSECURE_COOKIE", "HTTPONLY_COOKIE", "PERMISSIVE_CORS",
    "TRUST_BOUNDARY_VIOLATION", "IMPROPER_UNICODE",
    "HEADER_INJECTION", "RESPONSE_SPLITTING",
)

# Priority → severity label
_PRIORITY = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}

# ── Report file patterns ──────────────────────────────────────────────────────

_REPORT_PATTERNS = [
    "target/spotbugsXml.xml",
    "target/spotbugs.xml",
    "build/reports/spotbugs/main.xml",
    "build/reports/spotbugs/spotbugs.xml",
    "**/spotbugsXml.xml",
    "**/spotbugs.xml",
]

# ── SpotBugs / findsecbugs JAR search ─────────────────────────────────────────

def _find_spotbugs_jar() -> str | None:
    """Find the main spotbugs JAR in ~/.m2."""
    m2 = Path("~/.m2/repository/com/github/spotbugs/spotbugs").expanduser()
    if not m2.is_dir():
        return None
    jars = [j for j in m2.rglob("spotbugs-*.jar")
            if "annotations" not in j.name and "sources" not in j.name
            and j.stat().st_size > 1_000_000]
    return str(sorted(jars, reverse=True)[0]) if jars else None


def _find_findsecbugs_jar() -> str | None:
    """Find the findsecbugs plugin JAR in ~/.m2."""
    m2 = Path("~/.m2/repository/com/h3xstream/findsecbugs").expanduser()
    if m2.is_dir():
        jars = list(m2.rglob("findsecbugs-plugin-*.jar"))
        if jars:
            return str(sorted(jars, reverse=True)[0])
    # Also check common manual install paths
    for p in [Path("~/tools/findsecbugs").expanduser(),
              Path("/opt/findsecbugs")]:
        if p.is_dir():
            jars = list(p.glob("findsecbugs-plugin-*.jar"))
            if jars:
                return str(jars[0])
    return None


def _find_reports(root: Path) -> list[str]:
    found = []
    for pat in _REPORT_PATTERNS:
        for p in root.glob(pat):
            if p.stat().st_size > 0:
                found.append(str(p.relative_to(root)))
    return found


def _has_pom(root: Path) -> bool:
    return (root / "pom.xml").is_file()


def _has_gradle(root: Path) -> bool:
    return (root / "build.gradle").is_file() or (root / "build.gradle.kts").is_file()


# ── XML report parser ─────────────────────────────────────────────────────────

def _is_security_bug(bug_type: str, category: str) -> bool:
    if category in SECURITY_CATEGORIES:
        return True
    return any(bug_type.startswith(p) for p in SECURITY_BUG_PREFIXES)


def _parse_spotbugs_xml(path: Path, security_only: bool = True) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()

    all_bugs: list[dict] = []
    security_bugs: list[dict] = []

    for bug in root.findall(".//BugInstance"):
        btype    = bug.get("type", "")
        category = bug.get("category", "")
        priority = int(bug.get("priority", 3))
        rank     = int(bug.get("rank", 20))

        # Source location
        src = bug.find("SourceLine")
        if src is None:
            src = bug.find(".//SourceLine")
        file_path = src.get("sourcepath", "") if src is not None else ""
        start_line = src.get("start", "?")  if src is not None else "?"

        # Class and method
        cls = bug.find("Class")
        cls_name = cls.get("classname", "") if cls is not None else ""
        method = bug.find("Method")
        method_name = method.get("name", "") if method is not None else ""

        # Messages
        short_msg = (bug.findtext("ShortMessage") or "").strip()
        long_msg  = (bug.findtext("LongMessage")  or "").strip()

        entry = {
            "type":        btype,
            "category":    category,
            "severity":    _PRIORITY.get(priority, "LOW"),
            "rank":        rank,
            "file":        file_path,
            "line":        start_line,
            "class":       cls_name,
            "method":      method_name,
            "message":     long_msg or short_msg,
        }
        all_bugs.append(entry)
        if _is_security_bug(btype, category):
            security_bugs.append(entry)

    target = security_bugs if security_only else all_bugs
    target.sort(key=lambda b: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(b["severity"], 3), b["rank"]))

    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for b in target:
        counts[b["severity"]] = counts.get(b["severity"], 0) + 1

    return {
        "total_bugs":          len(all_bugs),
        "security_bugs":       len(security_bugs),
        "by_severity":         counts,
        "has_high":            counts["HIGH"] > 0,
        "findings":            target,
        "security_only":       security_only,
    }


# ── run() ─────────────────────────────────────────────────────────────────────

def run(
    *,
    action:        str = "scan",
    report:        str | None = None,
    security_only: bool = True,
    binary:        str | None = None,
    cwd:           str | None = None,
) -> ForgeResult:
    with Timer() as t:
        base = Path(cwd or ".").resolve()
        import shutil

        # ── find ──────────────────────────────────────────────────────────
        if action == "find":
            sb_jar  = _find_spotbugs_jar()
            fsb_jar = _find_findsecbugs_jar()
            mvn     = shutil.which("mvn")
            gradle  = shutil.which("gradle") or shutil.which("./gradlew")
            reports = _find_reports(base)

            ready = bool((mvn and _has_pom(base)) or (gradle and _has_gradle(base)) or sb_jar)

            return ForgeResult.success(TOOL, {
                "ready":              ready,
                "spotbugs_jar":       sb_jar,
                "findsecbugs_jar":    fsb_jar,
                "findsecbugs_found":  fsb_jar is not None,
                "mvn":                mvn,
                "gradle":             shutil.which("gradle"),
                "has_pom":            _has_pom(base),
                "has_gradle":         _has_gradle(base),
                "existing_reports":   reports,
                "install_hint": (
                    None if ready else
                    "Add spotbugs-maven-plugin to pom.xml (Maven) or spotbugs plugin to build.gradle,\n"
                    "or download findsecbugs from https://find-sec-bugs.github.io/"
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
                    TOOL, ["No SpotBugs XML report found"],
                    t.elapsed_ms,
                    suggestion=(
                        "Run action=scan first, or:\n"
                        "  Maven:  mvn com.github.spotbugs:spotbugs-maven-plugin:spotbugs\n"
                        "  Gradle: gradle spotbugsMain"
                    ),
                )
            try:
                data = _parse_spotbugs_xml(target, security_only)
                data["report_file"] = str(target.relative_to(base))
            except ET.ParseError as e:
                return ForgeResult.failure(TOOL, [f"XML parse error: {e}"], t.elapsed_ms)

            return ForgeResult(
                ok=not data["has_high"],
                tool=TOOL,
                data=data,
                errors=(
                    [f"{data['by_severity']['HIGH']} HIGH severity security findings"]
                    if data["has_high"] else []
                ),
                duration_ms=t.elapsed_ms,
            )

        # ── scan ──────────────────────────────────────────────────────────
        if action == "scan":
            mvn    = shutil.which("mvn")
            gradle = shutil.which("gradle")

            if mvn and _has_pom(base):
                cmd = [
                    mvn, "-q",
                    "com.github.spotbugs:spotbugs-maven-plugin:spotbugs",
                    "-Dspotbugs.xmlOutput=true",
                    "-Dspotbugs.includeFilterFile=",  # all bugs
                ]
                fsb = _find_findsecbugs_jar()
                if fsb:
                    cmd += [f"-Dspotbugs.pluginList={fsb}"]
                rc, stdout, stderr = run_command(cmd, cwd=str(base), timeout=300)

            elif gradle and _has_gradle(base):
                cmd = [gradle if gradle else "./gradlew", "spotbugsMain", "--no-daemon"]
                rc, stdout, stderr = run_command(cmd, cwd=str(base), timeout=300)

            else:
                return ForgeResult.failure(
                    TOOL,
                    ["No Maven pom.xml or Gradle build file found — cannot auto-scan"],
                    t.elapsed_ms,
                    suggestion=(
                        "Add spotbugs-maven-plugin to your pom.xml:\n"
                        "  <plugin>\n"
                        "    <groupId>com.github.spotbugs</groupId>\n"
                        "    <artifactId>spotbugs-maven-plugin</artifactId>\n"
                        "    <version>4.8.6.0</version>\n"
                        "  </plugin>\n"
                        "Then run: forge security spotbugs --action scan"
                    ),
                )

            # Try to parse the generated report
            existing = _find_reports(base)
            if existing:
                rpath = base / existing[0]
                try:
                    data = _parse_spotbugs_xml(rpath, security_only)
                    data["report_file"] = existing[0]
                    return ForgeResult(
                        ok=not data["has_high"],
                        tool=TOOL,
                        data=data,
                        errors=(
                            [f"{data['by_severity']['HIGH']} HIGH severity findings"]
                            if data["has_high"] else []
                        ),
                        duration_ms=t.elapsed_ms,
                    )
                except Exception as exc:
                    return ForgeResult.failure(TOOL, [f"Report parse error: {exc}"], t.elapsed_ms)

            if rc != 0:
                return ForgeResult.failure(
                    TOOL, [stderr.strip() or f"SpotBugs exited {rc}"], t.elapsed_ms
                )

            return ForgeResult.success(TOOL, {
                "scanned": True, "stdout": stdout[:1000]
            }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL, [f"Unknown action '{action}'. Use: scan | report | find"], t.elapsed_ms
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="scan",
                   choices=["scan", "report", "find"],
                   help="scan: run + parse | report: parse existing XML | find: locate tools")
    p.add_argument("--report", default=None,
                   help="Path to existing SpotBugsXml.xml report")
    p.add_argument("--all-bugs", action="store_false", dest="security_only",
                   help="Include all SpotBugs findings, not just security-related")
    p.add_argument("--binary", default=None, help="Override spotbugs binary path")
    p.add_argument("--cwd", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "SpotBugs + Find Security Bugs — Java static security analysis", run, _add_args)
