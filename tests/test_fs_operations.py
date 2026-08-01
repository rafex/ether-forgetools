from __future__ import annotations

from pathlib import Path

from forgetools.fs.operations import run


def test_fs_info_reports_missing_and_existing_paths(tmp_path: Path) -> None:
    missing = run(action="info", cwd=str(tmp_path), path="missing.txt")
    assert missing.ok
    assert missing.data["exists"] is False

    file = tmp_path / "sample.txt"
    file.write_text("sample\n", encoding="utf-8")
    existing = run(action="info", cwd=str(tmp_path), path="sample.txt")
    assert existing.ok
    assert existing.data["type"] == "file"
    assert existing.data["size_bytes"] > 0


def test_fs_mutations_preview_then_execute(tmp_path: Path) -> None:
    preview = run(action="mkdir", cwd=str(tmp_path), path="nested/deep")
    assert preview.ok and preview.data["preview"] is True
    assert not (tmp_path / "nested" / "deep").exists()

    created = run(
        action="mkdir",
        cwd=str(tmp_path),
        path="nested/deep",
        execute=True,
        confirm=True,
    )
    assert created.ok and (tmp_path / "nested" / "deep").is_dir()

    touched = run(
        action="touch",
        cwd=str(tmp_path),
        path="nested/deep/file.txt",
        execute=True,
        confirm=True,
    )
    assert touched.ok and (tmp_path / "nested" / "deep" / "file.txt").is_file()


def test_fs_archive_extract_and_delete_are_guarded(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("payload\n", encoding="utf-8")
    archive = tmp_path / "bundle.tar.gz"
    extracted = tmp_path / "extracted"

    archived = run(
        action="archive",
        cwd=str(tmp_path),
        sources="source.txt",
        destination="bundle.tar.gz",
        execute=True,
        confirm=True,
    )
    assert archived.ok and archive.is_file()

    extracted_result = run(
        action="extract",
        cwd=str(tmp_path),
        source="bundle.tar.gz",
        destination="extracted",
        execute=True,
        confirm=True,
    )
    assert extracted_result.ok
    assert (extracted / "source.txt").read_text(encoding="utf-8") == "payload\n"

    unsafe = run(action="delete", cwd=str(tmp_path), path=".", execute=True, confirm=True)
    assert not unsafe.ok
    assert "working directory" in unsafe.errors[0]

    deleted = run(
        action="delete",
        cwd=str(tmp_path),
        path="extracted",
        recursive=True,
        execute=True,
        confirm=True,
    )
    assert deleted.ok and not extracted.exists()


def test_fs_delete_removes_symlink_without_following_it(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("keep me\n", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    deleted = run(
        action="delete",
        cwd=str(tmp_path),
        path="link.txt",
        execute=True,
        confirm=True,
    )

    assert deleted.ok
    assert not link.exists()
    assert target.read_text(encoding="utf-8") == "keep me\n"
