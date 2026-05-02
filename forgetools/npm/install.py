"""forgetools.npm.install — Run npm install."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "npm.install"


def run(*, cwd: str | None = None, frozen: bool = False) -> ForgeResult:
    with Timer() as t:
        # Use npm ci for frozen/reproducible installs, npm install otherwise
        cmd = ["npm", "ci"] if frozen else ["npm", "install"]
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, ["npm not found"], t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"npm install failed (rc={rc})"],
                t.elapsed_ms,
            )

        packages_added = _parse_added(stdout)
        return ForgeResult.success(TOOL, {
            "packages_added": packages_added,
            "stdout": stdout,
        }, t.elapsed_ms)


def _parse_added(output: str) -> int:
    m = re.search(r"added (\d+) package", output)
    if m:
        return int(m.group(1))
    return 0


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--frozen", action="store_true",
                   help="Use npm ci for frozen/reproducible install")


if __name__ == "__main__":
    make_cli(TOOL, "Run npm install", run, _add_args)
