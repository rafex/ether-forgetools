"""forgetools.java.maven — Run Maven goals with structured output."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "java.maven"


def run(
    *,
    cwd: str | None = None,
    goal: str = "verify",
    module: str | None = None,
    profiles: str | None = None,
    skip_tests: bool = False,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["mvn", *goal.split()]
        if module:
            cmd += ["-pl", module, "-am"]
        if profiles:
            cmd += [f"-P{profiles}"]
        if skip_tests:
            cmd += ["-DskipTests"]
        cmd += ["-B", "--no-transfer-progress"]

        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["mvn not found"], suggestion="Install Maven: brew install maven")

        data = _parse(stdout, rc)
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [data.get("build_status", "BUILD FAILURE")],
                duration_ms=t.elapsed_ms,
                suggestion="Check build errors in the 'errors' field",
            )
        return ForgeResult.success(TOOL, data, t.elapsed_ms)


def _parse(stdout: str, rc: int) -> dict:
    errors = []
    warnings = []
    tests_run = tests_failed = tests_errors = tests_skipped = 0

    for line in stdout.splitlines():
        if "[ERROR]" in line:
            errors.append(line.strip())
        elif "[WARNING]" in line:
            warnings.append(line.strip())
        m = re.search(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)", line)
        if m:
            tests_run += int(m.group(1))
            tests_failed += int(m.group(2))
            tests_errors += int(m.group(3))
            tests_skipped += int(m.group(4))

    build_status = "BUILD SUCCESS" if rc == 0 else "BUILD FAILURE"
    return {
        "build_status": build_status,
        "tests": {
            "run": tests_run,
            "failed": tests_failed,
            "errors": tests_errors,
            "skipped": tests_skipped,
        },
        "errors": errors,
        "warnings": warnings[:20],
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--goal", default="verify")
    p.add_argument("--module", default=None)
    p.add_argument("--profiles", default=None)
    p.add_argument("--skip-tests", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "Run Maven goals", run, _add_args)
