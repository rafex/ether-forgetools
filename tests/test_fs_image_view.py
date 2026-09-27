from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

from forgetools.fs import image_view


def test_image_view_returns_bounded_preview_metadata_and_colors(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "rgb.png"
    Image.new("RGB", (320, 120), "#336699").save(image_path)
    monkeypatch.setattr(image_view, "_ocr", lambda *_: {"available": False, "text": "", "reason": "test"})

    result = image_view.run(path="rgb.png", cwd=str(tmp_path), preview_width=12, preview_height=6)

    assert result.ok
    assert result.data["dimensions"] == {"width": 320, "height": 120}
    assert result.data["preview_dimensions"]["width"] <= 12
    assert result.data["preview_dimensions"]["height"] <= 6
    assert result.data["dominant_colors"][0]["hex"] == "#336699"


def test_image_view_supports_grayscale_and_alpha(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(image_view, "_ocr", lambda *_: {"available": False, "text": "", "reason": "test"})
    for mode in ("L", "RGBA"):
        image_path = tmp_path / f"{mode}.png"
        color = 128 if mode == "L" else (50, 100, 150, 80)
        Image.new(mode, (8, 4), color).save(image_path)

        result = image_view.run(path=str(image_path), ocr=False)

        assert result.ok
        assert result.data["mode"] == mode
        assert result.data["preview"]

    transparent = tmp_path / "transparent.png"
    Image.new("RGBA", (8, 4), (0, 0, 0, 0)).save(transparent)
    transparent_result = image_view.run(path=str(transparent), ocr=False)
    assert transparent_result.ok
    assert transparent_result.data["dominant_colors"][0]["hex"] == "#FFFFFF"


def test_image_view_applies_exif_orientation(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "oriented.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (20, 10), "white").save(image_path, exif=exif)
    monkeypatch.setattr(image_view, "_ocr", lambda *_: {"available": False, "text": "", "reason": "test"})

    result = image_view.run(path=str(image_path), ocr=False)

    assert result.ok
    assert result.data["dimensions"] == {"width": 20, "height": 10}
    assert result.data["display_dimensions"] == {"width": 10, "height": 20}
    assert result.data["exif_orientation"] == 6


def test_image_view_rejects_corrupt_and_oversized_input(tmp_path: Path, monkeypatch) -> None:
    corrupt = tmp_path / "broken.png"
    corrupt.write_bytes(b"not an image")
    assert not image_view.run(path=str(corrupt), ocr=False).ok

    oversized = tmp_path / "large.png"
    oversized.write_bytes(b"12345")
    monkeypatch.setattr(image_view, "MAX_FILE_BYTES", 4)
    result = image_view.run(path=str(oversized), ocr=False)
    assert not result.ok
    assert "byte limit" in result.errors[0]


def test_image_view_rejects_images_over_pixel_limit(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "pixels.png"
    Image.new("RGB", (10, 10), "white").save(image_path)
    monkeypatch.setattr(image_view, "MAX_PIXELS", 99)

    result = image_view.run(path=str(image_path), ocr=False)

    assert not result.ok
    assert "pixel limit" in result.errors[0]


def test_ocr_reports_missing_tesseract_or_language(monkeypatch) -> None:
    monkeypatch.setattr(image_view.shutil, "which", lambda _: None)
    missing_binary = image_view._ocr(Image.new("RGB", (4, 4)), "spa+eng")
    assert missing_binary["available"] is False
    assert "not found" in missing_binary["reason"]

    monkeypatch.setattr(image_view.shutil, "which", lambda _: "/usr/bin/tesseract")
    monkeypatch.setattr(
        image_view.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "List of available languages (1):\neng\n", ""),
    )
    missing_language = image_view._ocr(Image.new("RGB", (4, 4)), "spa+eng")
    assert missing_language["available"] is False
    assert missing_language["reason"] == "Tesseract language data missing: spa"


def test_ocr_passes_in_memory_image_to_tesseract(monkeypatch) -> None:
    monkeypatch.setattr(image_view.shutil, "which", lambda _: "/usr/bin/tesseract")
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if args[1] == "--list-langs":
            return subprocess.CompletedProcess(args, 0, "List of available languages (2):\neng\nspa\n", "")
        assert isinstance(kwargs["input"], bytes)
        return subprocess.CompletedProcess(args, 0, b"texto detectado\n", b"")

    monkeypatch.setattr(image_view.subprocess, "run", fake_run)
    result = image_view._ocr(Image.new("RGB", (8, 4), "white"), "spa+eng")

    assert result["available"] is True
    assert result["text"] == "texto detectado"
    assert calls[1][0][:4] == ["/usr/bin/tesseract", "stdin", "stdout", "-l"]


def test_image_view_rejects_unsafe_preview_dimensions(tmp_path: Path) -> None:
    result = image_view.run(path="missing.png", cwd=str(tmp_path), preview_width=1000)
    assert not result.ok
    assert "preview_width" in result.errors[0]
