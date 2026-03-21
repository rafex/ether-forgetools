"""forgetools.git.log — Git commit history."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "git.log"
SEP = "\x1f"


def run(
    *,
    cwd: str | None = None,
    max_count: int = 20,
    path: str | None = None,
    author: str | None = None,
    since: str | None = None,
) -> ForgeResult:
    fmt = SEP.join(["%H", "%h", "%an", "%ae", "%ai", "%s", "%D"])
    cmd = ["git", "log", f"--pretty=format:{fmt}", f"-n{max_count}"]
    if author:
        cmd += [f"--author={author}"]
    if since:
        cmd += [f"--since={since}"]
    if path:
        cmd += ["--", path]

    return run_and_build(
        cmd,
        tool_name=TOOL,
        cwd=cwd,
        data_fn=_parse,
        suggestion_on_fail="Run inside a git repository",
    )


def _parse(stdout: str, _stderr: str) -> list[dict]:
    commits = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split(SEP)
        if len(parts) < 7:
            continue
        commits.append(
            {
                "hash": parts[0],
                "short_hash": parts[1],
                "author": parts[2],
                "email": parts[3],
                "date": parts[4],
                "subject": parts[5],
                "refs": [r.strip() for r in parts[6].split(",") if r.strip()],
            }
        )
    return commits


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--max-count", type=int, default=20)
    p.add_argument("--path", default=None)
    p.add_argument("--author", default=None)
    p.add_argument("--since", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Show git commit history", run, _add_args)
