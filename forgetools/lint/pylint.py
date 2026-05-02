"""forgetools.lint.pylint — Run Pylint and parse JSON output."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "lint.pylint"


def run(*, path: str = ".", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        cmd = ["pylint", "--output-format=json", path]
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(
                TOOL,
                ["pylint not found"],
                t.elapsed_ms,
                suggestion="Install pylint: pip install pylint",
            )
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        # rc=0: no issues, rc=4: warnings only, both are ok=True
        # rc=1: fatal, rc=2: error, rc=32: usage error
        if rc not in (0, 4):
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"pylint exited with code {rc}"],
                t.elapsed_ms,
            )

        try:
            data = _parse(stdout)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Failed to parse pylint output: {e}"], t.elapsed_ms)


def _parse(output: str) -> dict:
    items = json.loads(output) if output.strip() else []
    total = errors = warnings = conventions = refactors = 0
    messages: list[dict] = []

    for item in items:
        msg_type = item.get("type", "")
        total += 1
        if msg_type == "error" or msg_type == "fatal":
            errors += 1
        elif msg_type == "warning":
            warnings += 1
        elif msg_type == "convention":
            conventions += 1
        elif msg_type == "refactor":
            refactors += 1
        messages.append({
            "file": item.get("path", ""),
            "line": item.get("line", 0),
            "col": item.get("column", 0),
            "type": msg_type,
            "message": item.get("message", ""),
            "symbol": item.get("symbol", ""),
        })

    return {
        "total": total,
        "errors": errors,
        "warnings": warnings,
        "conventions": conventions,
        "refactors": refactors,
        "messages": messages,
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".", help="Path to lint")


if __name__ == "__main__":
    make_cli(TOOL, "Run Pylint and parse results", run, _add_args)
