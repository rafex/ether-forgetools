"""forgetools.npm.audit — Run npm audit and parse JSON output."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "npm.audit"


def run(*, cwd: str | None = None, level: str = "high") -> ForgeResult:
    with Timer() as t:
        cmd = ["npm", "audit", "--json"]
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["npm not found"], t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        # rc != 0 just means vulnerabilities were found — still parse output
        try:
            data = _parse(stdout, level)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Failed to parse npm audit output: {e}"], t.elapsed_ms)


def _parse(output: str, _level: str) -> dict:
    parsed = json.loads(output) if output.strip() else {}

    # npm audit v7+ format
    meta = parsed.get("metadata", {})
    vulns_meta = meta.get("vulnerabilities", {})

    critical = vulns_meta.get("critical", 0)
    high = vulns_meta.get("high", 0)
    moderate = vulns_meta.get("moderate", 0)
    low = vulns_meta.get("low", 0)
    total = vulns_meta.get("total", critical + high + moderate + low)

    vulnerabilities: list[dict] = []
    for name, vuln in parsed.get("vulnerabilities", {}).items():
        vulnerabilities.append({
            "name": name,
            "severity": vuln.get("severity", ""),
            "via": [v if isinstance(v, str) else v.get("title", "") for v in vuln.get("via", [])],
            "range": vuln.get("range", ""),
        })

    return {
        "total": total,
        "critical": critical,
        "high": high,
        "moderate": moderate,
        "low": low,
        "vulnerabilities": vulnerabilities,
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--level", default="high",
                   choices=["low", "moderate", "high", "critical"],
                   help="Minimum severity level to report")


if __name__ == "__main__":
    make_cli(TOOL, "Run npm audit and parse results", run, _add_args)
