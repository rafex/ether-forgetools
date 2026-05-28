"""forgetools.websearch.visit — Visit a URL and extract readable content."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.web import fetch as web_fetch

TOOL = "websearch.visit"


def run(
    *,
    url: str,
    xpath: str | None = None,
    max_chars: int = 8000,
    include_links: bool = False,
    include_headings: bool = True,
    timeout: int = 20,
    user_agent: str = web_fetch._DEFAULT_UA,
    insecure: bool = False,
    cwd: str | None = None,
) -> ForgeResult:
    """Visit a URL and return parsed text/metadata for browsing workflows."""
    with Timer() as t:
        result = web_fetch.run(
            url=url,
            xpath=xpath,
            max_chars=max_chars,
            include_links=include_links,
            include_headings=include_headings,
            timeout=timeout,
            user_agent=user_agent,
            insecure=insecure,
            cwd=cwd,
        )
        if result.ok:
            return ForgeResult.success(TOOL, result.data, t.elapsed_ms)
        return ForgeResult.failure(
            TOOL,
            result.errors,
            t.elapsed_ms,
            suggestion=result.suggestion,
        )


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", required=True)
    parser.add_argument("--xpath", default=None)
    parser.add_argument("--max-chars", type=int, default=8000)
    parser.add_argument("--include-links", action="store_true")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--user-agent", default=web_fetch._DEFAULT_UA)
    parser.add_argument("--insecure", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "Visit a URL and extract readable content", run, _add_args)
