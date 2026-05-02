"""forgetools.git.blame — Git blame with structured output."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "git.blame"


def run(
    *,
    cwd: str | None = None,
    file: str,
    lines: str | None = None,
) -> ForgeResult:
    cmd = ["git", "blame", "--line-porcelain"]
    if lines:
        cmd += [f"-L{lines}"]
    cmd.append(file)
    return run_and_build(
        cmd,
        tool_name=TOOL,
        cwd=cwd,
        data_fn=_parse,
        suggestion_on_fail="Run inside a git repository with a valid file path",
    )


def _parse(stdout: str, _stderr: str) -> list[dict]:
    entries = []
    current: dict = {}
    for line in stdout.splitlines():
        if len(line) == 40 and all(c in "0123456789abcdef" for c in line[:8]):
            parts = line.split()
            current = {"commit": parts[0], "orig_line": parts[1], "final_line": parts[2]}
        elif line.startswith("author "):
            current["author"] = line[7:]
        elif line.startswith("author-time "):
            current["timestamp"] = line[12:]
        elif line.startswith("summary "):
            current["summary"] = line[8:]
        elif line.startswith("\t"):
            current["code"] = line[1:]
            entries.append(current)
            current = {}
    return entries


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True)
    p.add_argument("--lines", default=None, help="Line range, e.g. 10,50")


if __name__ == "__main__":
    make_cli(TOOL, "Show git blame", run, _add_args)
