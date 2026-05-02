"""forgetools.java.gradle — Run Gradle tasks with structured output."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "java.gradle"


def run(
    *,
    cwd: str | None = None,
    task: str = "build",
    module: str | None = None,
    skip_tests: bool = False,
) -> ForgeResult:
    with Timer() as t:
        # prefer wrapper if available
        import os
        gradle_cmd = "./gradlew" if os.path.exists(os.path.join(cwd or ".", "gradlew")) else "gradle"
        prefix = f"{module}:" if module else ""
        cmd = [gradle_cmd, f"{prefix}{task}", "--console=plain"]
        if skip_tests:
            cmd += ["-x", "test"]

        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["gradle not found"], suggestion="Install Gradle or use a project with gradlew")

        errors = [l.strip() for l in stdout.splitlines() if re.search(r"^(FAILURE|error:)", l, re.I)]
        status = "BUILD SUCCESSFUL" if rc == 0 else "BUILD FAILED"

        data = {"build_status": status, "errors": errors}
        if rc != 0:
            return ForgeResult.failure(TOOL, [status], duration_ms=t.elapsed_ms, suggestion="Check errors field")
        return ForgeResult.success(TOOL, data, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--task", default="build")
    p.add_argument("--module", default=None)
    p.add_argument("--skip-tests", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "Run Gradle tasks", run, _add_args)
