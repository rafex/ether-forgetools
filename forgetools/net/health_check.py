"""forgetools.net.health_check — Check if a service endpoint is healthy."""
from __future__ import annotations

import argparse
import time
import urllib.error
import urllib.request

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "net.health_check"


def run(
    *,
    cwd: str | None = None,
    url: str,
    expected_status: int = 200,
    timeout: int = 10,
) -> ForgeResult:
    with Timer() as t:
        try:
            start = time.monotonic()
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                latency = int((time.monotonic() - start) * 1000)
                healthy = resp.status == expected_status
                return ForgeResult(
                    ok=healthy,
                    tool=TOOL,
                    data={"url": url, "status": resp.status, "healthy": healthy, "latency_ms": latency},
                    duration_ms=t.elapsed_ms,
                    suggestion=f"Expected {expected_status}, got {resp.status}" if not healthy else None,
                )
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], duration_ms=t.elapsed_ms, suggestion=f"Service at {url} may be down")


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--url", required=True)
    p.add_argument("--expected-status", type=int, default=200)
    p.add_argument("--timeout", type=int, default=10)


if __name__ == "__main__":
    make_cli(TOOL, "Check if a service endpoint is healthy", run, _add_args)
