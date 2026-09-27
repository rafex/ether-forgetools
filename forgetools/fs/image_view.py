from __future__ import annotations

"""Text-only visual inspection for local raster images."""

import argparse
import io
import re
import shutil
import subprocess
import warnings
from pathlib import Path
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "fs.image-view"
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_PREVIEW_WIDTH = 120
MAX_PREVIEW_HEIGHT = 60
MAX_OCR_TEXT = 12_000
MAX_OCR_DIMENSION = 2_400
ASCII_RAMP = "@%#*+=-:. "


def _composite_on_white(image: Any) -> Any:
    if "A" not in image.getbands() and "transparency" not in image.info:
        return image
    from PIL import Image

    rgba = image.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(background, rgba).convert("RGB")


def _ascii_preview(image: Any, max_width: int, max_height: int) -> str:
    scale = min(
        1.0,
        max_width / image.width,
        (max_height * 2) / image.height,
    )
    width = max(1, round(image.width * scale))
    height = max(1, round(image.height * scale / 2))
    grayscale = _composite_on_white(image.resize((width, height))).convert("L")
    pixels = grayscale.tobytes()
    rows = []
    for row in range(height):
        values = pixels[row * width : (row + 1) * width]
        rows.append("".join(ASCII_RAMP[value * (len(ASCII_RAMP) - 1) // 255] for value in values))
    return "\n".join(rows)


def _dominant_colors(image: Any, count: int = 5) -> list[dict[str, str | float]]:
    scale = min(1.0, 256 / max(image.size))
    sampled = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))))
    rgb = _composite_on_white(sampled).convert("RGB")
    quantized = rgb.quantize(colors=count)
    histogram = quantized.getcolors(maxcolors=rgb.width * rgb.height) or []
    total = rgb.width * rgb.height
    palette = quantized.getpalette() or []
    colors = []
    for pixels, index in sorted(histogram, reverse=True)[:count]:
        offset = index * 3
        red, green, blue = palette[offset : offset + 3]
        colors.append({
            "hex": f"#{red:02X}{green:02X}{blue:02X}",
            "percentage": round(pixels * 100 / total, 1),
        })
    return colors


def _ocr(image: Any, languages: str) -> dict[str, Any]:
    executable = shutil.which("tesseract")
    if not executable:
        return {"available": False, "text": "", "reason": "Tesseract executable not found"}

    try:
        listed = subprocess.run(
            [executable, "--list-langs"], capture_output=True, text=True,
            timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "text": "", "reason": f"Could not inspect Tesseract languages: {exc}"}
    if listed.returncode != 0:
        return {"available": False, "text": "", "reason": listed.stderr.strip() or "Could not inspect Tesseract languages"}

    available_languages = set(listed.stdout.splitlines()[1:])
    requested_languages = languages.split("+")
    missing = [language for language in requested_languages if language not in available_languages]
    if missing:
        return {
            "available": False,
            "text": "",
            "reason": f"Tesseract language data missing: {', '.join(missing)}",
            "requested_languages": requested_languages,
            "available_languages": sorted(available_languages),
        }

    scale = min(1.0, MAX_OCR_DIMENSION / max(image.size))
    if scale < 1:
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))))
    ocr_image = _composite_on_white(image).convert("L")
    encoded = io.BytesIO()
    ocr_image.save(encoded, format="PNG")
    try:
        result = subprocess.run(
            [executable, "stdin", "stdout", "-l", languages, "--psm", "6"],
            input=encoded.getvalue(), capture_output=True, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "text": "", "reason": f"Tesseract OCR failed: {exc}"}
    if result.returncode != 0:
        reason = result.stderr.decode("utf-8", errors="replace").strip() or f"Tesseract exited with code {result.returncode}"
        return {"available": False, "text": "", "reason": reason}
    text = result.stdout.decode("utf-8", errors="replace").strip()
    return {
        "available": True,
        "text": text[:MAX_OCR_TEXT],
        "truncated": len(text) > MAX_OCR_TEXT,
        "languages": requested_languages,
    }


def run(
    *,
    path: str,
    cwd: str | None = None,
    preview_width: int = 80,
    preview_height: int = 40,
    ocr: bool = True,
    ocr_languages: str = "spa+eng",
) -> ForgeResult:
    """Inspect a raster image as bounded text, color metadata, and optional OCR."""
    with Timer() as timer:
        if not 1 <= preview_width <= MAX_PREVIEW_WIDTH:
            return ForgeResult.failure(TOOL, [f"preview_width must be between 1 and {MAX_PREVIEW_WIDTH}"], timer.elapsed_ms)
        if not 1 <= preview_height <= MAX_PREVIEW_HEIGHT:
            return ForgeResult.failure(TOOL, [f"preview_height must be between 1 and {MAX_PREVIEW_HEIGHT}"], timer.elapsed_ms)
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+", ocr_languages):
            return ForgeResult.failure(TOOL, ["ocr_languages contains unsupported characters"], timer.elapsed_ms)

        requested_path = Path(path).expanduser()
        if not requested_path.is_absolute():
            requested_path = Path(cwd or ".").expanduser() / requested_path
        try:
            image_path = requested_path.resolve(strict=True)
            if not image_path.is_file():
                return ForgeResult.failure(TOOL, [f"Not a regular file: {image_path}"], timer.elapsed_ms)
            file_size = image_path.stat().st_size
            if file_size > MAX_FILE_BYTES:
                return ForgeResult.failure(
                    TOOL,
                    [f"Image file exceeds the {MAX_FILE_BYTES}-byte limit ({file_size} bytes)"],
                    timer.elapsed_ms,
                    suggestion="Resize or convert the image before inspection.",
                )
        except FileNotFoundError:
            return ForgeResult.failure(TOOL, [f"Image file not found: {requested_path}"], timer.elapsed_ms)
        except OSError as exc:
            return ForgeResult.failure(TOOL, [f"Could not access image: {exc}"], timer.elapsed_ms)

        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
        except ImportError as exc:
            return ForgeResult.failure(
                TOOL,
                [str(exc)],
                timer.elapsed_ms,
                suggestion="Install the file MCP dependencies with `make install-mcp-file`.",
            )

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(image_path) as source:
                    width, height = source.size
                    if width * height > MAX_PIXELS:
                        return ForgeResult.failure(
                            TOOL,
                            [f"Image exceeds the {MAX_PIXELS}-pixel limit ({width}x{height})"],
                            timer.elapsed_ms,
                            suggestion="Resize the image before inspection.",
                        )
                    image_format = source.format
                    image_mode = source.mode
                    frame_count = getattr(source, "n_frames", 1)
                    orientation = source.getexif().get(274, 1)
                    source.seek(0)
                    source.load()
                    displayed = ImageOps.exif_transpose(source).copy()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            return ForgeResult.failure(TOOL, [f"Invalid or unsafe image: {exc}"], timer.elapsed_ms)
        except Exception as exc:
            return ForgeResult.failure(TOOL, [f"Could not decode image: {exc}"], timer.elapsed_ms)

        preview = _ascii_preview(displayed, preview_width, preview_height)
        preview_rows = preview.splitlines()
        colors = _dominant_colors(displayed)
        ocr_result = _ocr(displayed, ocr_languages) if ocr else {"available": False, "text": "", "reason": "OCR disabled"}
        return ForgeResult.success(TOOL, {
            "path": str(image_path),
            "format": image_format,
            "mode": image_mode,
            "size_bytes": file_size,
            "dimensions": {"width": width, "height": height},
            "display_dimensions": {"width": displayed.width, "height": displayed.height},
            "exif_orientation": orientation,
            "frames": frame_count,
            "preview": preview,
            "preview_dimensions": {"width": max((len(row) for row in preview_rows), default=0), "height": len(preview_rows)},
            "dominant_colors": colors,
            "ocr": ocr_result,
            "semantic_description": None,
        }, timer.elapsed_ms)


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", required=True, help="Image path, absolute or relative to --cwd")
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--preview-width", type=int, default=80)
    parser.add_argument("--preview-height", type=int, default=40)
    parser.add_argument("--no-ocr", dest="ocr", action="store_false", default=True)
    parser.add_argument("--ocr-languages", default="spa+eng", help="Plus-separated Tesseract language codes")


if __name__ == "__main__":
    make_cli(TOOL, "Inspect a local raster image as bounded text, color metadata, and optional OCR", run, _add_args)
