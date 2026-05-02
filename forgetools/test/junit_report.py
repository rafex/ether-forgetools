"""forgetools.test.junit_report — Parse JUnit XML test reports."""
from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "test.junit_report"


def run(*, path: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            base = Path(cwd or ".") / path
            xml_files = _collect_xml_files(base)
            if not xml_files:
                return ForgeResult.failure(
                    TOOL,
                    [f"No JUnit XML files found at: {path}"],
                    t.elapsed_ms,
                    suggestion="Check that tests have been run and report files exist",
                )
            data = _parse_all(xml_files)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)


def _collect_xml_files(base: Path) -> list[Path]:
    if base.is_file():
        return [base]
    files: list[Path] = []
    if base.is_dir():
        for root, _dirs, fnames in os.walk(base):
            for fname in fnames:
                if fname.startswith("TEST-") and fname.endswith(".xml"):
                    files.append(Path(root) / fname)
            surefire = Path(root) / "surefire-reports"
            if surefire.is_dir():
                for fname in os.listdir(surefire):
                    if fname.endswith(".xml"):
                        p = surefire / fname
                        if p not in files:
                            files.append(p)
    return files


def _parse_all(xml_files: list[Path]) -> dict:
    total = passed = failed = errors = skipped = 0
    duration_s = 0.0
    failures: list[dict] = []

    for f in xml_files:
        try:
            tree = ET.parse(f)
            root = tree.getroot()
            suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
            for suite in suites:
                total += int(suite.get("tests", 0))
                failed += int(suite.get("failures", 0))
                errors += int(suite.get("errors", 0))
                skipped += int(suite.get("skipped", 0))
                duration_s += float(suite.get("time", 0.0))
                for tc in suite.findall("testcase"):
                    for fail in list(tc.findall("failure")) + list(tc.findall("error")):
                        failures.append({
                            "test": tc.get("name", ""),
                            "classname": tc.get("classname", ""),
                            "message": fail.get("message", ""),
                            "stacktrace": (fail.text or "").strip(),
                        })
        except ET.ParseError:
            continue

    passed = total - failed - errors - skipped
    return {
        "total": total,
        "passed": max(passed, 0),
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "duration_s": round(duration_s, 3),
        "failures": failures,
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True, help="Path to JUnit XML file or directory")


if __name__ == "__main__":
    make_cli(TOOL, "Parse JUnit XML test reports", run, _add_args)
