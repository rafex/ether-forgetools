"""forgetools.office.pdf_merge - Merge PDFs using pdfunite or qpdf when available."""
from __future__ import annotations

import argparse
import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult
from forgetools._simple_tools import command_result


def run(*, inputs: str, output: str, cwd: str | None = None) -> ForgeResult:
    files = [item.strip() for item in inputs.split(",") if item.strip()]
    if not files:
        return ForgeResult.failure("office.pdf-merge", ["No input PDFs provided"], suggestion="Pass --inputs a.pdf,b.pdf")
    if shutil.which("pdfunite"):
        return command_result(tool="office.pdf-merge", cmd=["pdfunite", *files, output], cwd=cwd)
    if shutil.which("qpdf"):
        return command_result(tool="office.pdf-merge", cmd=["qpdf", "--empty", "--pages", *files, "--", output], cwd=cwd)
    return ForgeResult.failure(
        "office.pdf-merge",
        ["Neither pdfunite nor qpdf is installed"],
        suggestion="Install poppler-utils/pdfunite or qpdf.",
    )


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--inputs", required=True, help="Comma-separated PDF inputs")
    p.add_argument("--output", required=True, help="Merged PDF output")


if __name__ == "__main__":
    make_cli("office.pdf-merge", "Merge PDFs using pdfunite or qpdf", run, _args)
