"""forgetools.java.test_report — Parse JUnit/Surefire XML test reports."""
from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "java.test_report"


def run(*, cwd: str | None = None, path: str = "target/surefire-reports") -> ForgeResult:
    with Timer() as t:
        base = os.path.join(cwd or ".", path)
        if not os.path.isdir(base):
            return ForgeResult.failure(TOOL, [f"Directory not found: {base}"], suggestion="Run tests first: forge java maven --goal test")

        suites = []
        total = failed = errors = skipped = 0

        for fname in os.listdir(base):
            if not fname.endswith(".xml"):
                continue
            try:
                tree = ET.parse(os.path.join(base, fname))
                root = tree.getroot()
                suite_tests = int(root.get("tests", 0))
                suite_failed = int(root.get("failures", 0))
                suite_errors = int(root.get("errors", 0))
                suite_skipped = int(root.get("skipped", 0))
                failures = []
                for tc in root.findall("testcase"):
                    for fail in tc.findall("failure") + tc.findall("error"):
                        failures.append({
                            "test": f"{tc.get('classname')}.{tc.get('name')}",
                            "message": fail.get("message", ""),
                            "type": fail.get("type", ""),
                        })
                suites.append({
                    "name": root.get("name", fname),
                    "tests": suite_tests, "failed": suite_failed,
                    "errors": suite_errors, "skipped": suite_skipped,
                    "failures": failures,
                })
                total += suite_tests
                failed += suite_failed
                errors += suite_errors
                skipped += suite_skipped
            except Exception:
                continue

        return ForgeResult.success(TOOL, {
            "summary": {"total": total, "failed": failed, "errors": errors, "skipped": skipped, "passed": total - failed - errors - skipped},
            "suites": suites,
        }, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default="target/surefire-reports")


if __name__ == "__main__":
    make_cli(TOOL, "Parse JUnit/Surefire XML test reports", run, _add_args)
