"""forgetools.net.http_request — HTTP request with structured output."""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "net.http_request"


def run(
    *,
    cwd: str | None = None,
    url: str,
    method: str = "GET",
    body: str | None = None,
    header: list[str] | None = None,
    timeout: int = 30,
) -> ForgeResult:
    with Timer() as t:
        headers: dict[str, str] = {}
        for h in (header or []):
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()

        data = body.encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            start = time.monotonic()
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed = int((time.monotonic() - start) * 1000)
                raw = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                try:
                    parsed = json.loads(raw) if "json" in content_type else raw.decode("utf-8", errors="replace")
                except Exception:
                    parsed = raw.decode("utf-8", errors="replace")
                return ForgeResult.success(TOOL, {
                    "status": resp.status,
                    "content_type": content_type,
                    "latency_ms": elapsed,
                    "body": parsed,
                }, t.elapsed_ms)
        except urllib.error.HTTPError as e:
            return ForgeResult.failure(TOOL, [f"HTTP {e.code}: {e.reason}"], duration_ms=t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], duration_ms=t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--url", required=True)
    p.add_argument("--method", default="GET")
    p.add_argument("--body", default=None)
    p.add_argument("--header", action="append", default=[], help="Header in 'Key: Value' format")
    p.add_argument("--timeout", type=int, default=30)


if __name__ == "__main__":
    make_cli(TOOL, "Make an HTTP request", run, _add_args)
