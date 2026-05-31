"""forgetools.ai.ollama - Inspect or run Ollama models."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result


def run(*, action: str = "list", model: str = "", prompt: str = "", cwd: str | None = None) -> ForgeResult:
    if action == "list":
        cmd = ["ollama", "list"]
    elif action == "pull":
        cmd = ["ollama", "pull", model]
    elif action == "run":
        cmd = ["ollama", "run", model, prompt]
    else:
        return ForgeResult.failure("ai.ollama", [f"Unsupported action: {action}"], suggestion="Use list, pull, or run.")
    return command_result(tool="ai.ollama", cmd=cmd, cwd=cwd, suggestion="Install Ollama and ensure the daemon is running.")


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="list", choices=["list", "pull", "run"], help="Ollama action")
    p.add_argument("--model", default="", help="Model name for pull/run")
    p.add_argument("--prompt", default="", help="Prompt for run")


if __name__ == "__main__":
    make_cli("ai.ollama", "Inspect or run Ollama models", run, _args)
