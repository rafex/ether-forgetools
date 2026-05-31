"""forgetools.deps.npm - Fetch npm package metadata."""
from __future__ import annotations

import argparse
import json
import urllib.request

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer


def run(*, package: str, cwd: str | None = None) -> ForgeResult:
    del cwd
    with Timer() as t:
        url = f"https://registry.npmjs.org/{package}"
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return ForgeResult.failure("deps.npm", [str(exc)], t.elapsed_ms, "Check package name or network access.")
        latest = payload.get("dist-tags", {}).get("latest")
        return ForgeResult.success("deps.npm", {"package": package, "latest": latest, "description": payload.get("description"), "url": url}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True, help="npm package name")


if __name__ == "__main__":
    make_cli("deps.npm", "Fetch npm package metadata", run, _args)
