"""forgetools.office.pdf_append_tables - Append CSV/XLSX table pages to a PDF."""
from __future__ import annotations

import argparse
import tempfile

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.office._utils import resolve_path
from forgetools.office.table_report import run as table_report_run


def run(*, pdf: str, table: str, output: str, title: str = "Table Appendix", sheet: str | None = None, max_rows: int = 500, cwd: str | None = None) -> ForgeResult:
    with Timer() as timer:
        try:
            from pypdf import PdfReader, PdfWriter
        except Exception as exc:
            return ForgeResult.failure("office.pdf-append-tables", [str(exc)], timer.elapsed_ms, "Install pypdf in the office MCP environment.")

        pdf_path = resolve_path(cwd, pdf)
        table_path = resolve_path(cwd, table)
        output_path = resolve_path(cwd, output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            table_pdf = tmp.name
        report = table_report_run(input=str(table_path), output=table_pdf, output_format="pdf", title=title, sheet=sheet, max_rows=max_rows, cwd=None)
        if not report.ok:
            return ForgeResult.failure("office.pdf-append-tables", report.errors, timer.elapsed_ms, report.suggestion)

        writer = PdfWriter()
        for reader_path in (pdf_path, table_pdf):
            reader = PdfReader(str(reader_path))
            for page in reader.pages:
                writer.add_page(page)
        with output_path.open("wb") as f:
            writer.write(f)
        return ForgeResult.success("office.pdf-append-tables", {"pdf": str(pdf_path), "table": str(table_path), "output": str(output_path)}, timer.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pdf", required=True, help="Base PDF")
    p.add_argument("--table", required=True, help="CSV/TSV/XLSX table to append")
    p.add_argument("--output", required=True, help="Output PDF")
    p.add_argument("--title", default="Table Appendix", help="Table appendix title")
    p.add_argument("--sheet", default=None, help="Worksheet name for XLSX inputs")
    p.add_argument("--max-rows", default=500, type=int, help="Maximum rows to read")


if __name__ == "__main__":
    make_cli("office.pdf-append-tables", "Append CSV/XLSX table pages to a PDF", run, _args)
