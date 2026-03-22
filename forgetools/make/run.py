"""forgetools.make.run — Run make targets or list available targets."""
from __future__ import annotations

import argparse
import os
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "make.run"


def run(*, target: str = "", cwd: str | None = None, list_targets: bool = False) -> ForgeResult:
    with Timer() as t:
        if list_targets:
            return _list_targets(cwd, t)
        return _run_target(target, cwd, t)


def _list_targets(cwd: str | None, t) -> ForgeResult:
    base = cwd or os.getcwd()
    makefile_path = os.path.join(base, "Makefile")
    if not os.path.isfile(makefile_path):
        return ForgeResult.failure(
            TOOL, ["Makefile not found in cwd"],
            duration_ms=t.elapsed_ms, suggestion="Run from directory containing a Makefile"
        )
    try:
        with open(makefile_path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError as e:
        return ForgeResult.failure(TOOL, [str(e)], duration_ms=t.elapsed_ms)

    phony: set[str] = set()
    for line in content.splitlines():
        m = re.match(r"^\.PHONY\s*:\s*(.+)$", line)
        if m:
            phony.update(n.strip() for n in m.group(1).split())

    targets: list[dict] = []
    seen: set[str] = set()
    for line in content.splitlines():
        m = re.match(r"^([\w][\w\-]*)\s*:[^=].*?(?:##\s*(.+))?$", line)
        if m:
            name = m.group(1)
            if name in seen:
                continue
            seen.add(name)
            desc_raw = m.group(2)
            description = desc_raw.strip() if desc_raw else None
            targets.append({"name": name, "description": description, "phony": name in phony})

    return ForgeResult.success(TOOL, {"targets": targets}, t.elapsed_ms)


def _run_target(target: str, cwd: str | None, t) -> ForgeResult:
    cmd = ["make"]
    if target:
        cmd.append(target)
    try:
        rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
    except FileNotFoundError:
        return ForgeResult.failure(TOOL, ["make not found"], suggestion="Install make")
    combined_out = (stdout + "\n" + stderr).strip()
    return ForgeResult.success(
        TOOL,
        {"target": target, "stdout": combined_out[:4096], "returncode": rc},
        t.elapsed_ms,
    )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--target", default="", help="Make target to run")
    p.add_argument("--list-targets", action="store_true", default=False,
                   help="List available targets instead of running")


if __name__ == "__main__":
    make_cli(TOOL, "Run make targets or list available targets", run, _add_args)
