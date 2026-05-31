"""forgetools.office.pdf_text - Extract text from a PDF using pdftotext."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result


def run(*, input: str, output: str = "-", cwd: str | None = None) -> ForgeResult:
    return command_result(
        tool="office.pdf-text",
        cmd=["pdftotext", input, output],
        cwd=cwd,
        suggestion="Install poppler-utils/pdftotext.",
    )


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--input", required=True, help="PDF input")
    p.add_argument("--output", default="-", help="Text output path or '-'")


if __name__ == "__main__":
    make_cli("office.pdf-text", "Extract text from PDF", run, _args)
