"""forgetools.shell.run — Execute arbitrary shell commands."""
from __future__ import annotations

import argparse
import shlex
import subprocess

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "shell.run"


def run(
    *,
    cmd: str,
    cwd: str | None = None,
    timeout: int = 60,
    max_bytes: int = 8192,
) -> ForgeResult:
    with Timer() as t:
        try:
            args = shlex.split(cmd)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
            )
        except FileNotFoundError as e:
            return ForgeResult.failure(TOOL, [f"Command not found: {e}"], t.elapsed_ms)
        except subprocess.TimeoutExpired:
            return ForgeResult.failure(TOOL, [f"Command timed out after {timeout}s"], t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        stdout = result.stdout
        stderr = result.stderr
        truncated = False

        if len(stdout.encode()) > max_bytes:
            stdout = stdout.encode()[:max_bytes].decode(errors="replace")
            truncated = True
        if len(stderr.encode()) > max_bytes:
            stderr = stderr.encode()[:max_bytes].decode(errors="replace")
            truncated = True

        data = {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
            "truncated": truncated,
            "cmd": cmd,
        }
        return ForgeResult.success(TOOL, data, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--cmd", required=True, help="Shell command to execute")
    p.add_argument("--timeout", type=int, default=60, help="Timeout in seconds")
    p.add_argument("--max-bytes", type=int, default=8192, dest="max_bytes",
                   help="Max bytes to capture per stream")


if __name__ == "__main__":
    make_cli(TOOL, "Execute arbitrary shell command", run, _add_args)
