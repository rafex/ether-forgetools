"""Shell command runner with structured error handling."""
from __future__ import annotations

import subprocess
from typing import Any, Callable, Sequence

from ._result import ForgeResult, Timer


def run_command(
    cmd: str | Sequence[str],
    *,
    cwd: str | None = None,
    input_text: str | None = None,
    env: dict | None = None,
    timeout: int = 120,
) -> tuple[int, str, str]:
    """Run a command, return (returncode, stdout, stderr)."""
    if isinstance(cmd, str):
        import shlex
        args = shlex.split(cmd)
    else:
        args = list(cmd)

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=cwd,
        input=input_text,
        env=env,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def run_and_build(
    cmd: str | Sequence[str],
    *,
    tool_name: str,
    data_fn: Callable[[str, str], Any],
    cwd: str | None = None,
    suggestion_on_fail: str | None = None,
    timeout: int = 120,
) -> ForgeResult:
    """Run a command and build a ForgeResult using data_fn(stdout, stderr)."""
    with Timer() as t:
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=timeout)
            if rc != 0:
                return ForgeResult.failure(
                    tool_name,
                    errors=[stderr.strip() or f"Exited with code {rc}"],
                    duration_ms=t.elapsed_ms,
                    suggestion=suggestion_on_fail,
                )
            return ForgeResult.success(tool_name, data_fn(stdout, stderr), t.elapsed_ms)
        except FileNotFoundError as e:
            return ForgeResult.failure(
                tool_name,
                errors=[f"Command not found: {e}"],
                duration_ms=t.elapsed_ms,
                suggestion=suggestion_on_fail,
            )
        except subprocess.TimeoutExpired:
            return ForgeResult.failure(
                tool_name,
                errors=["Command timed out"],
                duration_ms=t.elapsed_ms,
            )
        except Exception as e:
            return ForgeResult.failure(
                tool_name,
                errors=[str(e)],
                duration_ms=t.elapsed_ms,
            )
