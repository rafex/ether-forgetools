"""forgetools.office.pdf_metadata - Extract PDF metadata, page count, and document flags."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.office._utils import resolve_path


def run(*, input: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            from pypdf import PdfReader
        except Exception as exc:
            return ForgeResult.failure("office.pdf-metadata", [str(exc)], t.elapsed_ms, "Install pypdf in the office MCP environment.")
        path = resolve_path(cwd, input)
        reader = PdfReader(str(path))
        metadata = {str(k).lstrip("/"): str(v) for k, v in (reader.metadata or {}).items()}
        return ForgeResult.success("office.pdf-metadata", {"input": str(path), "pages": len(reader.pages), "encrypted": reader.is_encrypted, "metadata": metadata}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--input", required=True, help="PDF input")


if __name__ == "__main__":
    make_cli("office.pdf-metadata", "Extract PDF metadata, page count, and document flags", run, _args)
