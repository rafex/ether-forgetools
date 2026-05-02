"""forgetools.search.grep — Structured grep over project files."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "search.grep"


def run(
    *,
    cwd: str | None = None,
    pattern: str,
    path: str = ".",
    file_ext: str | None = None,
    context: int = 0,
    ignore_case: bool = False,
    max_results: int = 200,
) -> ForgeResult:
    with Timer() as t:
        try:
            cmd = ["grep", "-rn", "--color=never"]
            if ignore_case:
                cmd.append("-i")
            if context > 0:
                cmd += [f"-C{context}"]
            if file_ext:
                cmd += ["--include", f"*{file_ext}"]
            cmd += [pattern, path]

            rc, stdout, stderr = run_command(cmd, cwd=cwd)
            # rc=1 means no matches (not an error)
            if rc > 1:
                return ForgeResult.failure(TOOL, [stderr.strip()], duration_ms=t.elapsed_ms)

            matches = _parse(stdout, max_results)
            return ForgeResult.success(
                TOOL,
                {"pattern": pattern, "match_count": len(matches), "matches": matches},
                t.elapsed_ms,
            )
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["grep not found"], duration_ms=t.elapsed_ms)


def _parse(stdout: str, max_results: int) -> list[dict]:
    matches = []
    for line in stdout.splitlines()[:max_results]:
        m = re.match(r"^(.+?):(\d+):(.*)", line)
        if m:
            matches.append({"file": m.group(1), "line": int(m.group(2)), "text": m.group(3)})
        elif line == "--":
            continue
        else:
            matches.append({"file": None, "line": None, "text": line})
    return matches


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pattern", required=True)
    p.add_argument("--path", default=".")
    p.add_argument("--file-ext", default=None)
    p.add_argument("--context", type=int, default=0)
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--max-results", type=int, default=200)


if __name__ == "__main__":
    make_cli(TOOL, "Search files with grep", run, _add_args)
