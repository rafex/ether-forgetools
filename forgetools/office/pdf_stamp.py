"""forgetools.office.pdf_stamp - Stamp text on each page of a PDF."""
from __future__ import annotations

import argparse
import tempfile

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.office._utils import resolve_path


def run(*, input: str, output: str, text: str, x: float = 36, y: float = 36, font_size: int = 10, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            from pypdf import PdfReader, PdfWriter
            from reportlab.pdfgen import canvas
        except Exception as exc:
            return ForgeResult.failure("office.pdf-stamp", [str(exc)], t.elapsed_ms, "Install pypdf and reportlab in the office MCP environment.")
        input_path = resolve_path(cwd, input)
        output_path = resolve_path(cwd, output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        reader = PdfReader(str(input_path))
        writer = PdfWriter()
        for page in reader.pages:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                stamp_path = tmp.name
            c = canvas.Canvas(stamp_path, pagesize=(width, height))
            c.setFont("Helvetica", font_size)
            c.drawString(x, y, text)
            c.save()
            stamp_page = PdfReader(stamp_path).pages[0]
            page.merge_page(stamp_page)
            writer.add_page(page)
        with output_path.open("wb") as f:
            writer.write(f)
        return ForgeResult.success("office.pdf-stamp", {"input": str(input_path), "output": str(output_path), "text": text, "pages": len(reader.pages)}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--input", required=True, help="PDF input")
    p.add_argument("--output", required=True, help="Stamped PDF output")
    p.add_argument("--text", required=True, help="Stamp text")
    p.add_argument("--x", default=36, type=float, help="X coordinate")
    p.add_argument("--y", default=36, type=float, help="Y coordinate")
    p.add_argument("--font-size", default=10, type=int, help="Stamp font size")


if __name__ == "__main__":
    make_cli("office.pdf-stamp", "Stamp text on each page of a PDF", run, _args)
