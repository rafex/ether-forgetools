"""forgetools.deps.pypi - Fetch PyPI package metadata."""
from __future__ import annotations

import argparse
import json
import urllib.request

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer


def run(*, package: str, cwd: str | None = None) -> ForgeResult:
    del cwd
    with Timer() as t:
        url = f"https://pypi.org/pypi/{package}/json"
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return ForgeResult.failure("deps.pypi", [str(exc)], t.elapsed_ms, "Check package name or network access.")
        info = payload.get("info", {})
        return ForgeResult.success("deps.pypi", {"package": package, "version": info.get("version"), "summary": info.get("summary"), "url": url}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True, help="PyPI package name")


if __name__ == "__main__":
    make_cli("deps.pypi", "Fetch PyPI package metadata", run, _args)
