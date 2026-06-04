"""forgetools.office.pdf_images - Extract embedded PDF page images when available."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.office._utils import resolve_path, sanitize_filename


def run(*, input: str, output_dir: str, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            from pypdf import PdfReader
        except Exception as exc:
            return ForgeResult.failure("office.pdf-images", [str(exc)], t.elapsed_ms, "Install pypdf in the office MCP environment.")
        input_path = resolve_path(cwd, input)
        out_dir = resolve_path(cwd, output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        reader = PdfReader(str(input_path))
        extracted = []
        for page_index, page in enumerate(reader.pages, start=1):
            for image_index, image in enumerate(getattr(page, "images", []), start=1):
                name = sanitize_filename(getattr(image, "name", "") or f"page-{page_index}-image-{image_index}")
                path = out_dir / f"p{page_index:03d}-{image_index:03d}-{name}"
                path.write_bytes(image.data)
                extracted.append(str(path))
        return ForgeResult.success("office.pdf-images", {"input": str(input_path), "output_dir": str(out_dir), "count": len(extracted), "files": extracted}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--input", required=True, help="PDF input")
    p.add_argument("--output-dir", required=True, help="Directory for extracted images")


if __name__ == "__main__":
    make_cli("office.pdf-images", "Extract embedded PDF page images when available", run, _args)
