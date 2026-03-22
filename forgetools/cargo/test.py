"""forgetools.cargo.test — Run cargo test and parse output."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "cargo.test"

_TEST_LINE = re.compile(r"^test (.+?) \.\.\. (ok|FAILED|ignored)$")
_FAILURE_START = re.compile(r"^---- (.+?) stdout ----$")


def run(
    *,
    cwd: str | None = None,
    package: str | None = None,
    test_filter: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["cargo", "test"]
        if package:
            cmd += ["--package", package]
        if test_filter:
            cmd.append(test_filter)
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["cargo not found"], t.elapsed_ms,
                                       suggestion="Install Rust: https://rustup.rs/")
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        # rc != 0 just means test failures — still parse
        combined = stdout + stderr
        try:
            data = _parse(combined)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Failed to parse cargo test output: {e}"], t.elapsed_ms)


def _parse(output: str) -> dict:
    total = passed = failed = 0
    failures: list[dict] = []
    failure_outputs: dict[str, list[str]] = {}
    current_failure: str | None = None

    for line in output.splitlines():
        m = _TEST_LINE.match(line)
        if m:
            test_name, result = m.group(1), m.group(2)
            total += 1
            if result == "ok":
                passed += 1
            elif result == "FAILED":
                failed += 1
            current_failure = None
            continue

        mf = _FAILURE_START.match(line)
        if mf:
            current_failure = mf.group(1)
            failure_outputs[current_failure] = []
            continue

        if current_failure is not None:
            if line.startswith("----"):
                current_failure = None
            else:
                failure_outputs[current_failure].append(line)

    for test_name, out_lines in failure_outputs.items():
        failures.append({"test": test_name, "output": "\n".join(out_lines).strip()})

    return {"total": total, "passed": passed, "failed": failed, "failures": failures}


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", default=None, help="Package to test")
    p.add_argument("--test-filter", default=None, dest="test_filter",
                   help="Run only tests matching this name")


if __name__ == "__main__":
    make_cli(TOOL, "Run cargo test and parse results", run, _add_args)
