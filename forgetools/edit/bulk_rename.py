"""forgetools.edit.bulk_rename — Rename files matching a pattern."""
from __future__ import annotations

import argparse
import os
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "edit.bulk_rename"


def run(
    *,
    cwd: str | None = None,
    path: str = ".",
    pattern: str,
    replacement: str,
    dry_run: bool = False,
) -> ForgeResult:
    with Timer() as t:
        base = os.path.join(cwd or ".", path)
        regex = re.compile(pattern)
        changes = []

        for root, _, files in os.walk(base):
            for fname in files:
                new_name = regex.sub(replacement, fname)
                if new_name != fname:
                    old_path = os.path.join(root, fname)
                    new_path = os.path.join(root, new_name)
                    rel_old = os.path.relpath(old_path, base)
                    rel_new = os.path.relpath(new_path, base)
                    changes.append({"from": rel_old, "to": rel_new})
                    if not dry_run:
                        os.rename(old_path, new_path)

        return ForgeResult.success(
            TOOL,
            {"dry_run": dry_run, "renamed": len(changes), "changes": changes},
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".")
    p.add_argument("--pattern", required=True)
    p.add_argument("--replacement", required=True)
    p.add_argument("--dry-run", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "Rename files matching a pattern", run, _add_args)
