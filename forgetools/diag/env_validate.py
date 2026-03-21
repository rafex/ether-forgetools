"""forgetools.diag.env_validate — Validate required environment variables."""
from __future__ import annotations

import argparse
import os
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "diag.env_validate"
SECRET_RE = re.compile(r"(password|secret|token|key|credential)", re.IGNORECASE)


def run(*, cwd: str | None = None, required: str) -> ForgeResult:
    with Timer() as t:
        vars_list = [v.strip() for v in required.split(",") if v.strip()]
        results = {}
        missing = []
        for var in vars_list:
            value = os.environ.get(var)
            is_secret = bool(SECRET_RE.search(var))
            results[var] = {
                "set": value is not None,
                "value": "***" if (value and is_secret) else (value or None),
            }
            if not value:
                missing.append(var)

        return ForgeResult(
            ok=len(missing) == 0,
            tool=TOOL,
            data={"variables": results, "missing": missing},
            duration_ms=t.elapsed_ms,
            suggestion=f"Set missing vars: export {missing[0]}=..." if missing else None,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--required", required=True, help="Comma-separated variable names")


if __name__ == "__main__":
    make_cli(TOOL, "Validate required environment variables", run, _add_args)
