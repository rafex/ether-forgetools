"""forgetools.office.pdf_merge - Merge PDFs using pypdf, pdfunite, or qpdf."""
from __future__ import annotations

import argparse
import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._simple_tools import command_result


def run(*, inputs: str, output: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        files = [item.strip() for item in inputs.split(",") if item.strip()]
        if not files:
            return ForgeResult.failure("office.pdf-merge", ["No input PDFs provided"], t.elapsed_ms, "Pass --inputs a.pdf,b.pdf")
        if shutil.which("pdfunite"):
            return command_result(tool="office.pdf-merge", cmd=["pdfunite", *files, output], cwd=cwd)
        if shutil.which("qpdf"):
            return command_result(tool="office.pdf-merge", cmd=["qpdf", "--empty", "--pages", *files, "--", output], cwd=cwd)
        try:
            from pypdf import PdfReader, PdfWriter
        except Exception as exc:
            return ForgeResult.failure("office.pdf-merge", [str(exc)], t.elapsed_ms, "Install pypdf, poppler-utils/pdfunite, or qpdf.")

        from pathlib import Path

        root = Path(cwd or ".").resolve()
        output_path = (root / output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        writer = PdfWriter()
        for file in files:
            reader = PdfReader(str((root / file).resolve()))
            for page in reader.pages:
                writer.add_page(page)
        with output_path.open("wb") as f:
            writer.write(f)
        return ForgeResult.success("office.pdf-merge", {"inputs": files, "output": str(output_path)}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--inputs", required=True, help="Comma-separated PDF inputs")
    p.add_argument("--output", required=True, help="Merged PDF output")


if __name__ == "__main__":
    make_cli("office.pdf-merge", "Merge PDFs using pypdf, pdfunite, or qpdf", run, _args)
