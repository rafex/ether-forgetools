"""forgetools.observability.log_tail - Tail logs with optional filtering."""
from __future__ import annotations

import argparse
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer


def run(*, file: str, lines: int = 100, grep: str = "", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        path = (Path(cwd or ".") / file).resolve()
        all_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        tail = all_lines[-lines:]
        if grep:
            tail = [line for line in tail if grep in line]
        return ForgeResult.success("observability.log-tail", {"file": str(path), "lines": tail, "count": len(tail)}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True, help="Log file")
    p.add_argument("--lines", type=int, default=100, help="Lines to read from tail")
    p.add_argument("--grep", default="", help="Substring filter")


if __name__ == "__main__":
    make_cli("observability.log-tail", "Tail logs with optional filtering", run, _args)
