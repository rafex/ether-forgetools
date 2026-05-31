"""forgetools.cloud.whoami - Show active identity for AWS, GCP, or Azure."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result


def run(*, provider: str = "aws", cwd: str | None = None) -> ForgeResult:
    commands = {
        "aws": ["aws", "sts", "get-caller-identity"],
        "gcp": ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=json"],
        "azure": ["az", "account", "show"],
    }
    if provider not in commands:
        return ForgeResult.failure("cloud.whoami", [f"Unknown provider: {provider}"], suggestion="Use aws, gcp, or azure.")
    return command_result(tool="cloud.whoami", cmd=commands[provider], cwd=cwd, suggestion=f"Install and authenticate the {provider} CLI.")


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--provider", default="aws", choices=["aws", "gcp", "azure"], help="Cloud provider")


if __name__ == "__main__":
    make_cli("cloud.whoami", "Show active cloud identity", run, _args)
