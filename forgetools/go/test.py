"""forgetools.go.test — Run go test with JSON output parsing."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "go.test"


def run(
    *,
    path: str = "./...",
    cwd: str | None = None,
    verbose: bool = False,
    run: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["go", "test", "-json"]
        if verbose:
            cmd.append("-v")
        if run:
            cmd += ["-run", run]
        cmd.append(path)
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["go not found"], t.elapsed_ms,
                                       suggestion="Install Go: https://go.dev/doc/install")
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        # rc != 0 means test failures — still parse the output
        if rc != 0 and not stdout.strip():
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"go test failed (rc={rc})"],
                t.elapsed_ms,
            )

        try:
            data = _parse(stdout)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Failed to parse go test output: {e}"], t.elapsed_ms)


def _parse(output: str) -> dict:
    total = passed = failed = 0
    duration_s = 0.0
    failures: list[dict] = []
    test_outputs: dict[str, list[str]] = {}

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        action = obj.get("Action", "")
        test = obj.get("Test")
        pkg = obj.get("Package", "")
        elapsed = obj.get("Elapsed", 0.0)

        if test is None:
            # Package-level event
            if action == "pass":
                duration_s += elapsed
            continue

        key = f"{pkg}/{test}"
        if action == "run":
            total += 1
            test_outputs[key] = []
        elif action == "output":
            test_outputs.setdefault(key, []).append(obj.get("Output", ""))
        elif action == "pass":
            passed += 1
        elif action == "fail":
            failed += 1
            output_lines = "".join(test_outputs.get(key, []))
            failures.append({"test": test, "package": pkg, "output": output_lines.strip()})

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "duration_s": round(duration_s, 3),
        "failures": failures,
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default="./...", help="Package path to test")
    p.add_argument("--verbose", action="store_true", help="Verbose output")
    p.add_argument("--run", default=None, help="Run only tests matching regex")


if __name__ == "__main__":
    make_cli(TOOL, "Run go test and parse results", run, _add_args)
