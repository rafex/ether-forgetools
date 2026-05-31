"""forgetools.office.markdown_html - Convert Markdown to a standalone HTML document."""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer


def _simple_markdown(text: str) -> str:
    lines = []
    in_code = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            lines.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
            continue
        if in_code:
            lines.append(html.escape(line))
        elif line.startswith("# "):
            lines.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            lines.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            lines.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.startswith("- "):
            lines.append(f"<li>{html.escape(line[2:].strip())}</li>")
        elif line.strip():
            value = html.escape(line)
            value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
            lines.append(f"<p>{value}</p>")
    return "\n".join(lines)


def run(*, input: str, output: str = "", title: str = "Document", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        root = Path(cwd or ".").resolve()
        input_path = (root / input).resolve()
        output_path = (root / output).resolve() if output else input_path.with_suffix(".html")
        body = _simple_markdown(input_path.read_text(encoding="utf-8"))
        doc = f"<!doctype html><html><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title></head><body>\n{body}\n</body></html>\n"
        output_path.write_text(doc, encoding="utf-8")
        return ForgeResult.success("office.markdown-html", {"input": str(input_path), "output": str(output_path)}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--input", required=True, help="Markdown input file")
    p.add_argument("--output", default="", help="HTML output file")
    p.add_argument("--title", default="Document", help="HTML title")


if __name__ == "__main__":
    make_cli("office.markdown-html", "Convert Markdown to standalone HTML", run, _args)
