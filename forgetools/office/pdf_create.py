"""forgetools.office.pdf_create - Create a PDF from Markdown, HTML, or plain text."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.office._utils import plain_blocks, read_text, resolve_path


def run(*, input: str, output: str, source_format: str = "markdown", title: str = "Document", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer
        except Exception as exc:
            return ForgeResult.failure("office.pdf-create", [str(exc)], t.elapsed_ms, "Install reportlab in the office MCP environment.")

        root_input = resolve_path(cwd, input)
        output_path = resolve_path(cwd, output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        styles = getSampleStyleSheet()
        story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
        style_map = {"h1": "Heading1", "h2": "Heading2", "h3": "Heading3", "paragraph": "BodyText", "bullet": "BodyText"}
        for kind, value in plain_blocks(read_text(root_input), source_format):
            if kind == "code":
                story.append(Preformatted(value, styles["Code"]))
            elif kind == "bullet":
                story.append(Paragraph(f"• {value}", styles["BodyText"]))
            else:
                story.append(Paragraph(value, styles[style_map.get(kind, "BodyText")]))
            story.append(Spacer(1, 6))
        doc = SimpleDocTemplate(str(output_path), pagesize=letter, title=title)
        doc.build(story)
        return ForgeResult.success("office.pdf-create", {"input": str(root_input), "output": str(output_path), "title": title}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--input", required=True, help="Markdown, HTML, or text input")
    p.add_argument("--output", required=True, help="PDF output path")
    p.add_argument("--source-format", default="markdown", choices=["markdown", "html", "text"], help="Input format")
    p.add_argument("--title", default="Document", help="Document title")


if __name__ == "__main__":
    make_cli("office.pdf-create", "Create a PDF from Markdown, HTML, or plain text", run, _args)
