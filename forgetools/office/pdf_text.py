"""forgetools.office.pdf_text - Extract text from a PDF using pdftotext or pypdf."""
from __future__ import annotations

import argparse
import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._simple_tools import command_result
from forgetools.office._utils import resolve_path


def run(*, input: str, output: str = "-", cwd: str | None = None) -> ForgeResult:
    if shutil.which("pdftotext"):
        return command_result(
            tool="office.pdf-text",
            cmd=["pdftotext", input, output],
            cwd=cwd,
            suggestion="Install poppler-utils/pdftotext or use pypdf fallback.",
        )

    with Timer() as t:
        try:
            from pypdf import PdfReader
        except Exception as exc:
            return ForgeResult.failure("office.pdf-text", [str(exc)], t.elapsed_ms, "Install pypdf or poppler-utils/pdftotext.")
        input_path = resolve_path(cwd, input)
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(input_path)).pages)
        if output == "-":
            return ForgeResult.success("office.pdf-text", {"input": str(input_path), "text": text}, t.elapsed_ms)
        output_path = resolve_path(cwd, output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        return ForgeResult.success("office.pdf-text", {"input": str(input_path), "output": str(output_path)}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--input", required=True, help="PDF input")
    p.add_argument("--output", default="-", help="Text output path or '-'")


if __name__ == "__main__":
    make_cli("office.pdf-text", "Extract text from PDF using pdftotext or pypdf", run, _args)
