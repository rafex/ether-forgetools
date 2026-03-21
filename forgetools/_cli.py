"""CLI helpers for forgetools scripts."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Callable

from ._result import ForgeResult


def make_cli(
    tool_name: str,
    description: str,
    run_fn: Callable[..., ForgeResult],
    extra_args_fn: Callable[[argparse.ArgumentParser], None] | None = None,
) -> None:
    """Parse args and invoke run_fn, then print the result."""
    parser = argparse.ArgumentParser(
        prog=f"python -m forgetools.{tool_name.replace('.', '.')}",
        description=description,
    )
    parser.add_argument("--cwd", default=None, help="Working directory")
    parser.add_argument(
        "--raw", action="store_true", help="Output raw data only (no ForgeResult wrapper)"
    )

    if extra_args_fn:
        extra_args_fn(parser)

    args = vars(parser.parse_args())
    raw = args.pop("raw", False)

    result: ForgeResult = run_fn(**args)

    if raw:
        if result.ok and result.data is not None:
            print(json.dumps(result.data, indent=2, ensure_ascii=False, default=str))
        else:
            print(json.dumps({"errors": result.errors}, indent=2))
            sys.exit(1)
    else:
        result.print()
        if not result.ok:
            sys.exit(1)
