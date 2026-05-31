"""forgetools.observability.log_parse - Parse JSON lines logs and summarize levels."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer


def run(*, file: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        path = (Path(cwd or ".") / file).resolve()
        levels: Counter[str] = Counter()
        malformed = 0
        samples = []
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                obj = json.loads(line)
            except Exception:
                malformed += 1
                continue
            level = str(obj.get("level") or obj.get("severity") or obj.get("loglevel") or "unknown").lower()
            levels[level] += 1
            if len(samples) < 5:
                samples.append(obj)
        return ForgeResult.success("observability.log-parse", {"file": str(path), "levels": dict(levels), "malformed": malformed, "samples": samples}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True, help="JSON lines log file")


if __name__ == "__main__":
    make_cli("observability.log-parse", "Parse JSON lines logs", run, _args)
