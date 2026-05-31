"""Small helpers for command-backed tools."""
from __future__ import annotations

import json
import shutil
from typing import Sequence

from ._result import ForgeResult, Timer
from ._runner import run_command


def command_result(
    *,
    tool: str,
    cmd: Sequence[str],
    cwd: str | None = None,
    timeout: int = 120,
    suggestion: str | None = None,
) -> ForgeResult:
    """Run a command and return stdout/stderr as structured data."""
    with Timer() as t:
        executable = cmd[0]
        if shutil.which(executable) is None:
            return ForgeResult.failure(
                tool,
                [f"Command not found: {executable}"],
                t.elapsed_ms,
                suggestion=suggestion or f"Install `{executable}` or remove this tool from the workflow.",
            )
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=timeout)
        except Exception as exc:
            return ForgeResult.failure(tool, [str(exc)], t.elapsed_ms, suggestion=suggestion)

        data = {
            "command": list(cmd),
            "returncode": rc,
            "stdout": stdout,
            "stderr": stderr,
        }
        if rc != 0:
            return ForgeResult.failure(tool, [stderr.strip() or stdout.strip() or f"Exited with code {rc}"], t.elapsed_ms, suggestion=suggestion)
        return ForgeResult.success(tool, data, t.elapsed_ms)


def json_or_text(text: str):
    """Parse JSON when possible, otherwise return text."""
    try:
        return json.loads(text)
    except Exception:
        return text
