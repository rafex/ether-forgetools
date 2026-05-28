"""forgetools.websearch.ddg_search — Search the web with DuckDuckGo (DDGS)."""
from __future__ import annotations

import argparse
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "websearch.ddg_search"


def run(
    *,
    query: str,
    max_results: int = 10,
    source: str = "text",
    region: str = "wt-wt",
    safesearch: str = "moderate",
    timelimit: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    """Search DuckDuckGo using DDGS and return normalized JSON results."""
    with Timer() as t:
        try:
            from ddgs import DDGS  # type: ignore[import]
        except Exception as exc:
            return ForgeResult.failure(
                TOOL,
                [f"ddgs import failed: {exc}"],
                duration_ms=t.elapsed_ms,
                suggestion="Install optional dependency: pip install ddgs",
            )

        if not query.strip():
            return ForgeResult.failure(
                TOOL,
                ["query is required"],
                duration_ms=t.elapsed_ms,
                suggestion="Provide --query with non-empty text",
            )

        source_kind = source.strip().lower()
        if source_kind not in {"text", "news"}:
            return ForgeResult.failure(
                TOOL,
                [f"Unsupported source: {source}"],
                duration_ms=t.elapsed_ms,
                suggestion="Use source=text or source=news",
            )

        limit = max(1, min(max_results, 50))
        results: list[dict[str, Any]] = []

        try:
            with DDGS() as ddgs:
                if source_kind == "news":
                    iterator = ddgs.news(
                        query,
                        region=region,
                        safesearch=safesearch,
                        timelimit=timelimit,
                        max_results=limit,
                    )
                else:
                    iterator = ddgs.text(
                        query,
                        region=region,
                        safesearch=safesearch,
                        timelimit=timelimit,
                        max_results=limit,
                    )

                for item in iterator:
                    entry = _normalize_item(item, source_kind)
                    if entry:
                        results.append(entry)
        except Exception as exc:
            return ForgeResult.failure(
                TOOL,
                [f"DDGS search failed: {exc}"],
                duration_ms=t.elapsed_ms,
                suggestion="Retry with fewer max_results or a simpler query",
            )

        return ForgeResult.success(
            TOOL,
            {
                "query": query,
                "source": source_kind,
                "region": region,
                "safesearch": safesearch,
                "timelimit": timelimit,
                "result_count": len(results),
                "results": results,
            },
            t.elapsed_ms,
        )


def _normalize_item(item: dict[str, Any], source: str) -> dict[str, Any]:
    title = str(item.get("title") or item.get("headline") or "").strip()
    url = str(item.get("href") or item.get("url") or "").strip()
    snippet = str(item.get("body") or item.get("snippet") or "").strip()
    if not (title or url or snippet):
        return {}

    normalized: dict[str, Any] = {
        "title": title,
        "url": url,
        "snippet": snippet,
        "source": source,
    }
    if item.get("date"):
        normalized["date"] = item.get("date")
    if item.get("source"):
        normalized["publisher"] = item.get("source")
    return normalized


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query", required=True)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--source", default="text", choices=["text", "news"])
    parser.add_argument("--region", default="wt-wt")
    parser.add_argument("--safesearch", default="moderate", choices=["off", "moderate", "strict"])
    parser.add_argument("--timelimit", default=None, help="d, w, m, y (optional)")


if __name__ == "__main__":
    make_cli(TOOL, "Search the web with DuckDuckGo (DDGS)", run, _add_args)
