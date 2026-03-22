"""forgetools.gh.release — Create a GitHub release."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "gh.release"


def run(
    *,
    tag: str,
    title: str | None = None,
    notes: str | None = None,
    draft: bool = False,
    prerelease: bool = False,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        cmd = ["gh", "release", "create", tag]
        if title:
            cmd.extend(["--title", title])
        if notes is not None:
            cmd.extend(["--notes", notes])
        else:
            cmd.append("--generate-notes")
        if draft:
            cmd.append("--draft")
        if prerelease:
            cmd.append("--prerelease")

        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(
                TOOL, ["gh CLI not found"], suggestion="Install GitHub CLI: https://cli.github.com"
            )
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or "gh release create failed"],
                duration_ms=t.elapsed_ms,
                suggestion="Ensure you are authenticated: gh auth login",
            )

        url = _parse_url(stdout)
        return ForgeResult.success(
            TOOL,
            {"tag": tag, "url": url, "draft": draft, "prerelease": prerelease},
            t.elapsed_ms,
        )


def _parse_url(output: str) -> str:
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("http"):
            return line
    m = re.search(r"https://github\.com/\S+", output)
    return m.group(0) if m else output.strip()


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--tag", required=True, help="Tag name for the release")
    p.add_argument("--title", default=None)
    p.add_argument("--notes", default=None, help="Release notes (omit to auto-generate)")
    p.add_argument("--draft", action="store_true", default=False)
    p.add_argument("--prerelease", action="store_true", default=False)


if __name__ == "__main__":
    make_cli(TOOL, "Create a GitHub release", run, _add_args)
