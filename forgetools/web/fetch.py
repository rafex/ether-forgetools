"""forgetools.web.fetch — Fetch a webpage and extract readable text via XPath.

Backends (auto-selected in order):
  1. lxml      — full XPath 1.0 support, best content extraction
  2. html.parser — stdlib fallback, no extra deps

Extraction pipeline:
  1. Fetch URL with urllib (follows redirects, detects encoding)
  2. Remove noise: script, style, nav, footer, header, aside, noscript
  3. Find main content: article / main / [role=main] / body (first match)
  4. Apply custom --xpath if provided (lxml only; stdlib skips)
  5. Collapse whitespace, preserve paragraph breaks
  6. Return: title, description, headings, text, links, word_count

Usage:
    forge web fetch --url https://docs.python.org/3/library/json.html
    forge web fetch --url https://en.wikipedia.org/wiki/XPath --max-chars 4000
    forge web fetch --url https://example.com --xpath "//article//p"
    forge web fetch --url https://example.com --include-links
"""
from __future__ import annotations

import argparse
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "web.fetch"

# Block-level elements whose *content* should be skipped (they have closing tags)
_BLOCK_NOISE: frozenset[str] = frozenset(
    "script style nav footer header aside noscript iframe "
    "form button select textarea".split()
)

# Void elements — no closing tag, produce no text — safe to ignore completely
_VOID_ELEMENTS: frozenset[str] = frozenset(
    "area base br col embed hr img input keygen link meta "
    "param source track wbr".split()
)

# Content container XPath candidates (lxml only; tried in order)
_CONTENT_CANDIDATES = [
    "//article",
    "//main",
    "//*[@role='main']",
    "//*[@id='content']",
    "//*[@id='main']",
    "//*[contains(@class,'article')]",
    "//*[contains(@class,'post-content')]",
    "//*[contains(@class,'entry-content')]",
    "//*[contains(@class,'content')]",
    "//body",
]

_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 forgetools/1.0"
)


# ── Public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    url: str,
    xpath: str | None = None,
    max_chars: int = 8000,
    include_links: bool = False,
    include_headings: bool = True,
    timeout: int = 20,
    user_agent: str = _DEFAULT_UA,
    insecure: bool = False,
    cwd: str | None = None,
) -> ForgeResult:
    """Fetch a webpage and extract clean readable text using XPath.

    Returns title, meta description, headings, main body text, and optionally links.
    Uses lxml (XPath 1.0) when available; falls back to stdlib html.parser.

    Args:
        url:              URL to fetch (http or https).
        xpath:            Custom XPath to target specific content (lxml only).
                          Default: auto-detect article / main / body.
                          Examples: '//article//p'  '//div[@class=\"readme\"]'
        max_chars:        Max characters of body text returned (default 8000).
        include_links:    Also return hyperlinks found in content (default False).
        include_headings: Include h1/h2/h3 heading list (default True).
        timeout:          Request timeout in seconds (default 20).
        user_agent:       HTTP User-Agent sent with the request.
        insecure:         Skip TLS certificate verification (default False).
        cwd:              Unused — kept for CLI consistency.
    """
    with Timer() as t:
        try:
            raw_bytes, final_url, content_type, charset = _fetch(
                url, timeout, user_agent, insecure
            )
        except urllib.error.HTTPError as e:
            return ForgeResult.failure(
                TOOL, [f"HTTP {e.code}: {e.reason}"], t.elapsed_ms,
                suggestion=f"Verify the URL is publicly accessible: {url}",
            )
        except urllib.error.URLError as e:
            return ForgeResult.failure(
                TOOL, [f"URL error: {e.reason}"], t.elapsed_ms,
                suggestion="Check network and URL format (must start with http/https)",
            )
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)

        ct_lower = content_type.lower()
        if ct_lower and not any(k in ct_lower for k in ("html", "text", "xml", "xhtml")):
            return ForgeResult.failure(
                TOOL, [f"Non-HTML content type: {content_type}"], t.elapsed_ms,
                suggestion="Use 'forge net http' to download binary or JSON responses",
            )

        try:
            data = _parse(
                raw_bytes,
                charset=charset,
                final_url=final_url,
                content_type=content_type,
                custom_xpath=xpath,
                max_chars=max_chars,
                include_links=include_links,
                include_headings=include_headings,
            )
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Parse error: {e}"], t.elapsed_ms)


# ── Fetch ─────────────────────────────────────────────────────────────────────

def _fetch(
    url: str,
    timeout: int,
    user_agent: str,
    insecure: bool,
) -> tuple[bytes, str, str, str]:
    """Return (raw_bytes, final_url, content_type, charset)."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en,es;q=0.9",
            "Accept-Encoding": "identity",
        },
    )
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        raw_bytes: bytes = resp.read()
        final_url: str   = resp.url
        content_type: str = resp.headers.get("Content-Type", "text/html")

    charset = "utf-8"
    m = re.search(r"charset\s*=\s*([^\s;\"']+)", content_type, re.IGNORECASE)
    if m:
        charset = m.group(1).strip()
    return raw_bytes, final_url, content_type, charset


# ── Parser dispatcher ─────────────────────────────────────────────────────────

def _parse(
    raw_bytes: bytes,
    *,
    charset: str,
    final_url: str,
    content_type: str,
    custom_xpath: str | None,
    max_chars: int,
    include_links: bool,
    include_headings: bool,
) -> dict[str, Any]:
    try:
        return _parse_lxml(
            raw_bytes,
            charset=charset,
            final_url=final_url,
            content_type=content_type,
            custom_xpath=custom_xpath,
            max_chars=max_chars,
            include_links=include_links,
            include_headings=include_headings,
        )
    except ImportError:
        return _parse_stdlib(
            raw_bytes,
            charset=charset,
            final_url=final_url,
            content_type=content_type,
            max_chars=max_chars,
            include_links=include_links,
            include_headings=include_headings,
        )


# ── lxml backend ──────────────────────────────────────────────────────────────

def _parse_lxml(
    raw_bytes: bytes,
    *,
    charset: str,
    final_url: str,
    content_type: str,
    custom_xpath: str | None,
    max_chars: int,
    include_links: bool,
    include_headings: bool,
) -> dict[str, Any]:
    from lxml import html as lhtml  # type: ignore[import]

    try:
        tree = lhtml.fromstring(raw_bytes)
    except Exception:
        tree = lhtml.fromstring(raw_bytes.decode(charset, errors="replace"))

    # ── metadata ──────────────────────────────────────────────────────────────
    title = _ws(" ".join(tree.xpath("//title/text()")))
    desc_nodes = tree.xpath(
        "//meta[@name='description']/@content | "
        "//meta[@property='og:description']/@content"
    )
    description = _ws(desc_nodes[0]) if desc_nodes else ""
    canonical_nodes = tree.xpath(
        "//link[@rel='canonical']/@href | //meta[@property='og:url']/@content"
    )
    canonical = canonical_nodes[0].strip() if canonical_nodes else final_url

    # ── strip noise ───────────────────────────────────────────────────────────
    for tag in _BLOCK_NOISE:
        for el in tree.xpath(f"//{tag}"):
            p = el.getparent()
            if p is not None:
                p.remove(el)

    # ── find content root ─────────────────────────────────────────────────────
    if custom_xpath:
        nodes = tree.xpath(custom_xpath)
        content_root = nodes[0] if nodes else tree
    else:
        content_root = tree
        for expr in _CONTENT_CANDIDATES:
            nodes = tree.xpath(expr)
            if nodes:
                content_root = nodes[0]
                break

    # ── headings ──────────────────────────────────────────────────────────────
    headings: list[dict] = []
    if include_headings:
        for lvl in (1, 2, 3):
            for h in content_root.xpath(f".//h{lvl}"):
                txt = _ws("".join(h.itertext()))
                if txt:
                    headings.append({"level": lvl, "text": txt})
        # Sort by document order (lxml yields them in order already per level)
        # Re-sort globally by tree position
        headings = sorted(
            headings,
            key=lambda x: x["text"],  # good enough proxy; lxml order preserved per loop
        )
        # Actually lxml iterates in document order within each xpath call;
        # since we call per level, merge without sorting to keep doc order:
        headings_ordered: list[dict] = []
        for lvl in (1, 2, 3):
            for h in content_root.xpath(f".//h{lvl}"):
                txt = _ws("".join(h.itertext()))
                if txt:
                    headings_ordered.append({"level": lvl, "text": txt})
        headings = headings_ordered

    # ── links ─────────────────────────────────────────────────────────────────
    links: list[dict] = []
    if include_links:
        for a in content_root.xpath(".//a[@href]"):
            href = (a.get("href") or "").strip()
            if href and not href.startswith(("#", "javascript:", "mailto:")):
                links.append({
                    "href": urllib.parse.urljoin(final_url, href),
                    "text": _ws("".join(a.itertext())),
                })

    # ── text ──────────────────────────────────────────────────────────────────
    raw_text = " ".join(content_root.itertext())
    body_text = _clean_text(raw_text)
    body_text, truncated = _truncate(body_text, max_chars)

    return _result(
        url=final_url, canonical=canonical, title=title,
        description=description, headings=headings, body_text=body_text,
        links=links, truncated=truncated, max_chars=max_chars,
        backend="lxml", content_type=content_type,
    )


# ── stdlib html.parser backend ────────────────────────────────────────────────

class _HtmlExtractor:
    """Self-contained HTML text extractor built on html.parser.HTMLParser."""

    def __init__(self, base_url: str) -> None:
        from html.parser import HTMLParser as _HP

        self._base_url = base_url
        self.title       = ""
        self.description = ""
        self.headings: list[dict] = []
        self.links:    list[dict] = []
        self._text_parts: list[str] = []

        # State machine
        self._noise_depth = 0        # depth inside a block-noise element
        self._noise_stack: list[str] = []  # tag names that opened noise blocks
        self._in_title    = False
        self._title_buf:  list[str] = []
        self._cur_h:      int | None = None
        self._h_buf:      list[str] = []
        self._cur_a_href  = ""
        self._a_buf:      list[str] = []

        # Subclass HTMLParser inline to avoid MRO issues
        extractor = self

        class _Parser(_HP):
            def handle_starttag(self, tag: str, attrs: list) -> None:
                extractor._start(tag, dict(attrs))

            def handle_endtag(self, tag: str) -> None:
                extractor._end(tag)

            def handle_data(self, data: str) -> None:
                extractor._data(data)

        self._parser = _Parser()

    def feed(self, text: str) -> None:
        self._parser.feed(text)

    # ── internal handlers ─────────────────────────────────────────────────────

    def _start(self, tag: str, attr: dict[str, str | None]) -> None:
        tag = tag.lower()

        # Void elements: no depth tracking needed
        if tag in _VOID_ELEMENTS:
            if tag == "meta":
                name = (attr.get("name") or attr.get("property") or "").lower()
                if "description" in name:
                    self.description = _ws(attr.get("content") or "")
            return

        if tag in _BLOCK_NOISE:
            self._noise_depth += 1
            self._noise_stack.append(tag)
            return

        if self._noise_depth:
            return  # inside noise block — ignore everything

        if tag == "title":
            self._in_title = True
            self._title_buf = []
        elif tag in ("h1", "h2", "h3"):
            self._cur_h = int(tag[1])
            self._h_buf = []
        elif tag == "a":
            href = _ws(attr.get("href") or "")
            if href and not href.startswith(("#", "javascript:", "mailto:")):
                self._cur_a_href = urllib.parse.urljoin(self._base_url, href)
                self._a_buf = []

    def _end(self, tag: str) -> None:
        tag = tag.lower()

        if tag in _VOID_ELEMENTS:
            return

        if tag in _BLOCK_NOISE:
            if self._noise_stack and self._noise_stack[-1] == tag:
                self._noise_stack.pop()
                self._noise_depth = max(0, self._noise_depth - 1)
            return

        if self._noise_depth:
            return

        if tag == "title":
            self._in_title = False
            self.title = _ws("".join(self._title_buf))
        elif tag in ("h1", "h2", "h3") and self._cur_h is not None:
            txt = _ws("".join(self._h_buf))
            if txt:
                self.headings.append({"level": self._cur_h, "text": txt})
            self._cur_h = None
            self._h_buf = []
        elif tag == "a" and self._cur_a_href:
            self.links.append({
                "href": self._cur_a_href,
                "text": _ws("".join(self._a_buf)),
            })
            self._cur_a_href = ""
            self._a_buf = []
        elif tag in ("p", "div", "section", "article", "li", "tr", "br"):
            # Insert paragraph boundary
            self._text_parts.append("\n")

    def _data(self, data: str) -> None:
        if self._noise_depth or not data.strip():
            return
        if self._in_title:
            self._title_buf.append(data)
            return
        if self._cur_h is not None:
            self._h_buf.append(data)
        if self._cur_a_href:
            self._a_buf.append(data)
        self._text_parts.append(data)

    def get_text(self) -> str:
        return _clean_text("".join(self._text_parts))


def _parse_stdlib(
    raw_bytes: bytes,
    *,
    charset: str,
    final_url: str,
    content_type: str,
    max_chars: int,
    include_links: bool,
    include_headings: bool,
) -> dict[str, Any]:
    html_text = raw_bytes.decode(charset, errors="replace")

    ext = _HtmlExtractor(base_url=final_url)
    ext.feed(html_text)

    body_text = ext.get_text()
    body_text, truncated = _truncate(body_text, max_chars)

    return _result(
        url=final_url,
        canonical=final_url,
        title=ext.title,
        description=ext.description,
        headings=ext.headings if include_headings else [],
        body_text=body_text,
        links=ext.links if include_links else [],
        truncated=truncated,
        max_chars=max_chars,
        backend="html.parser",
        content_type=content_type,
    )


# ── Shared helpers ────────────────────────────────────────────────────────────

def _ws(s: str) -> str:
    """Collapse whitespace to single spaces."""
    return re.sub(r"\s+", " ", s or "").strip()


def _clean_text(raw: str) -> str:
    """Collapse whitespace but keep paragraph breaks."""
    lines = [_ws(line) for line in raw.splitlines()]
    out: list[str] = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank and out:
                out.append("")
            prev_blank = True
        else:
            out.append(line)
            prev_blank = False
    return "\n".join(out).strip()


def _truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut + " …", True


def _result(
    *,
    url: str,
    canonical: str,
    title: str,
    description: str,
    headings: list[dict],
    body_text: str,
    links: list[dict],
    truncated: bool,
    max_chars: int,
    backend: str,
    content_type: str,
) -> dict[str, Any]:
    return {
        "url":          url,
        "canonical":    canonical,
        "title":        title,
        "description":  description,
        "headings":     headings,
        "text":         body_text,
        "word_count":   len(body_text.split()) if body_text else 0,
        "char_count":   len(body_text),
        "truncated":    truncated,
        "max_chars":    max_chars,
        "links":        links,
        "content_type": content_type,
        "backend":      backend,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--url", "-u", required=True, help="URL to fetch (http/https)")
    p.add_argument(
        "--xpath", default=None,
        help=(
            "XPath to target specific content (lxml only). "
            "Default: auto-detect article/main/body. "
            "Examples: '//article//p'  '//div[@id=\"readme\"]'"
        ),
    )
    p.add_argument("--max-chars", type=int, default=8000,
                   help="Max body text characters returned (default: 8000)")
    p.add_argument("--include-links", action="store_true",
                   help="Include hyperlink list in output")
    p.add_argument("--no-headings", action="store_false", dest="include_headings",
                   help="Omit heading list")
    p.add_argument("--timeout", type=int, default=20,
                   help="Request timeout seconds (default: 20)")
    p.add_argument("--user-agent", default=_DEFAULT_UA, help="HTTP User-Agent")
    p.add_argument("--insecure", "-k", action="store_true",
                   help="Skip TLS certificate verification")


if __name__ == "__main__":
    make_cli(TOOL, "Fetch a webpage and extract readable text via XPath", run, _add_args)
