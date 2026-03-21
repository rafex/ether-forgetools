"""forgetools.docs.changelog — Generate changelog from git commits."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._runner import run_and_build

TOOL = "docs.changelog"

CONVENTIONAL_RE = re.compile(r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build)(?:\((.+)\))?!?:\s*(.+)")


def run(*, cwd: str | None = None, since: str | None = None, max_count: int = 100) -> ForgeResult:
    sep = "\x1f"
    fmt = sep.join(["%h", "%s", "%an", "%ai"])
    cmd = ["git", "log", f"--pretty=format:{fmt}", f"-n{max_count}"]
    if since:
        cmd += [f"--since={since}"]

    return run_and_build(
        cmd, tool_name=TOOL, cwd=cwd,
        data_fn=_parse,
        suggestion_on_fail="Run inside a git repository",
    )


def _parse(stdout: str, _stderr: str) -> dict:
    groups: dict[str, list[dict]] = {
        "feat": [], "fix": [], "docs": [], "refactor": [],
        "perf": [], "test": [], "chore": [], "other": [],
    }
    for line in stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) < 4:
            continue
        short_hash, subject, author, date = parts[0], parts[1], parts[2], parts[3]
        m = CONVENTIONAL_RE.match(subject)
        entry = {"hash": short_hash, "subject": subject, "author": author, "date": date[:10]}
        if m:
            category = m.group(1)
            entry["scope"] = m.group(2)
            entry["message"] = m.group(3)
            groups.setdefault(category, []).append(entry)
        else:
            groups["other"].append(entry)

    return {k: v for k, v in groups.items() if v}


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--since", default=None, help="e.g. '2 weeks ago' or a tag")
    p.add_argument("--max-count", type=int, default=100)


if __name__ == "__main__":
    make_cli(TOOL, "Generate changelog from git commits", run, _add_args)
