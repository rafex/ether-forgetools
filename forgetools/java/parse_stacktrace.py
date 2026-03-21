"""forgetools.java.parse_stacktrace — Parse Java stack traces into structured data."""
from __future__ import annotations

import argparse
import re
import sys

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "java.parse_stacktrace"

EXCEPTION_RE = re.compile(r"^([\w$.]+(?:Exception|Error|Throwable)[\w$.]*)(?::\s*(.*))?$")
FRAME_RE = re.compile(r"^\s+at ([\w$.]+)\.([\w$<>]+)\((.+):(\d+)\)$")
CAUSED_RE = re.compile(r"^Caused by: (.*)")


def run(*, cwd: str | None = None, file: str | None = None) -> ForgeResult:
    with Timer() as t:
        if file:
            try:
                with open(file, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except FileNotFoundError:
                return ForgeResult.failure(TOOL, [f"File not found: {file}"], duration_ms=t.elapsed_ms)
        else:
            text = sys.stdin.read()

        result = _parse(text)
        return ForgeResult.success(TOOL, result, t.elapsed_ms)


def _parse(text: str) -> dict:
    exceptions = []
    current_exc: dict | None = None
    frames: list[dict] = []

    for line in text.splitlines():
        line = line.rstrip()
        caused = CAUSED_RE.match(line)
        exc_m = EXCEPTION_RE.match(line.strip())
        frame_m = FRAME_RE.match(line)

        if caused:
            if current_exc is not None:
                current_exc["frames"] = frames
                exceptions.append(current_exc)
            inner = caused.group(1)
            parts = inner.split(":", 1)
            current_exc = {"type": parts[0].strip(), "message": parts[1].strip() if len(parts) > 1 else None, "caused_by": True, "frames": []}
            frames = []
        elif frame_m:
            frames.append({
                "class": frame_m.group(1),
                "method": frame_m.group(2),
                "file": frame_m.group(3),
                "line": int(frame_m.group(4)),
            })
        elif exc_m and not line.startswith("\t") and not line.startswith(" "):
            if current_exc is not None:
                current_exc["frames"] = frames
                exceptions.append(current_exc)
            current_exc = {"type": exc_m.group(1), "message": exc_m.group(2), "caused_by": False, "frames": []}
            frames = []

    if current_exc is not None:
        current_exc["frames"] = frames
        exceptions.append(current_exc)

    root = exceptions[0] if exceptions else None
    return {
        "exception_count": len(exceptions),
        "root_exception": root,
        "caused_by_chain": exceptions[1:] if len(exceptions) > 1 else [],
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", default=None, help="Read stacktrace from file (default: stdin)")


if __name__ == "__main__":
    make_cli(TOOL, "Parse Java stack traces", run, _add_args)
