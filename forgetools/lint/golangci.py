"""forgetools.lint.golangci — Run golangci-lint and parse JSON output."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "lint.golangci"


def run(*, path: str = "./...", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        cmd = ["golangci-lint", "run", "--out-format", "json", path]
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(
                TOOL,
                ["golangci-lint not found"],
                t.elapsed_ms,
                suggestion="Install golangci-lint: https://golangci-lint.run/usage/install/",
            )
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        # rc=1 means issues found, rc=0 means clean - both parseable
        if rc > 1:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"golangci-lint exited with code {rc}"],
                t.elapsed_ms,
            )

        try:
            data = _parse(stdout)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Failed to parse golangci-lint output: {e}"], t.elapsed_ms)


def _parse(output: str) -> dict:
    parsed = json.loads(output) if output.strip() else {}
    issues = parsed.get("Issues") or []

    files_map: dict[str, list[dict]] = {}
    for issue in issues:
        pos = issue.get("Pos", {})
        fname = pos.get("Filename", "")
        files_map.setdefault(fname, []).append({
            "line": pos.get("Line", 0),
            "col": pos.get("Column", 0),
            "severity": issue.get("Severity", "warning") or "warning",
            "message": issue.get("Text", ""),
            "linter": issue.get("FromLinter", ""),
        })

    files = [{"file": f, "violations": v} for f, v in files_map.items()]
    return {"total": len(issues), "files": files}


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default="./...", help="Path pattern to lint")


if __name__ == "__main__":
    make_cli(TOOL, "Run golangci-lint and parse results", run, _add_args)
