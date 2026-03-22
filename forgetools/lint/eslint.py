"""forgetools.lint.eslint — Run ESLint and parse JSON output."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "lint.eslint"

_SEVERITY = {1: "warning", 2: "error"}


def run(
    *,
    path: str = ".",
    cwd: str | None = None,
    config: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["eslint", "--format", "json", path]
        if config:
            cmd += ["--config", config]
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(
                TOOL,
                ["eslint not found"],
                t.elapsed_ms,
                suggestion="Run npm install to ensure eslint is available",
            )
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        # rc=1 means lint errors found (not a tool failure), rc=2 is a config error
        if rc == 2:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or "ESLint configuration error"],
                t.elapsed_ms,
                suggestion="Run npm install to ensure eslint is available",
            )

        try:
            data = _parse(stdout)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Failed to parse ESLint output: {e}"], t.elapsed_ms)


def _parse(output: str) -> dict:
    results = json.loads(output) if output.strip() else []
    total = errors = warnings = 0
    files: list[dict] = []

    for file_result in results:
        f_errors = file_result.get("errorCount", 0)
        f_warnings = file_result.get("warningCount", 0)
        messages: list[dict] = []
        for msg in file_result.get("messages", []):
            sev_int = msg.get("severity", 1)
            messages.append({
                "line": msg.get("line", 0),
                "col": msg.get("column", 0),
                "severity": _SEVERITY.get(sev_int, "warning"),
                "message": msg.get("message", ""),
                "rule": msg.get("ruleId") or "",
            })
        total += f_errors + f_warnings
        errors += f_errors
        warnings += f_warnings
        if messages:
            files.append({
                "file": file_result.get("filePath", ""),
                "errors": f_errors,
                "warnings": f_warnings,
                "messages": messages,
            })

    return {"total": total, "errors": errors, "warnings": warnings, "files": files}


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".", help="Path to lint")
    p.add_argument("--config", default=None, help="ESLint config file")


if __name__ == "__main__":
    make_cli(TOOL, "Run ESLint and parse results", run, _add_args)
