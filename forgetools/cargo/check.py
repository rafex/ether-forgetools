"""forgetools.cargo.check — Run cargo check and parse JSON output."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "cargo.check"


def run(*, cwd: str | None = None, package: str | None = None) -> ForgeResult:
    with Timer() as t:
        cmd = ["cargo", "check", "--message-format", "json"]
        if package:
            cmd += ["--package", package]
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["cargo not found"], t.elapsed_ms,
                                       suggestion="Install Rust: https://rustup.rs/")
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        try:
            data = _parse(stdout, rc)
            if rc != 0:
                return ForgeResult.failure(
                    TOOL,
                    [f"cargo check failed with {data['errors']} error(s)"],
                    t.elapsed_ms,
                )
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Failed to parse cargo output: {e}"], t.elapsed_ms)


def _parse(output: str, rc: int) -> dict:
    errors = warnings = 0
    messages: list[dict] = []

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        if obj.get("reason") != "compiler-message":
            continue

        msg = obj.get("message", {})
        level = msg.get("level", "")
        text = msg.get("message", "")
        spans = msg.get("spans", [])
        primary_span = next((s for s in spans if s.get("is_primary")), spans[0] if spans else {})
        fname: str | None = primary_span.get("file_name")
        line_num: int | None = primary_span.get("line_start")

        if level == "error":
            errors += 1
        elif level == "warning":
            warnings += 1

        messages.append({
            "level": level,
            "message": text,
            "file": fname,
            "line": line_num,
        })

    return {
        "ok": rc == 0,
        "errors": errors,
        "warnings": warnings,
        "messages": messages,
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", default=None, help="Package to check")


if __name__ == "__main__":
    make_cli(TOOL, "Run cargo check", run, _add_args)
