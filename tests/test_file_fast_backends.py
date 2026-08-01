from __future__ import annotations

from pathlib import Path

from forgetools.fs.disk_usage import run as disk_usage
from forgetools.fs.find_by_type import run as find_by_type
from forgetools.fs.read import run as read_file
from forgetools.search.find_files import run as find_files
from forgetools.search.grep import run as grep
from forgetools.search.search_replace import run as search_replace


def test_find_files_uses_fast_backend_when_available(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "alpha.py").write_text("alpha\n", encoding="utf-8")
    (tmp_path / "src" / "beta.txt").write_text("beta\n", encoding="utf-8")

    result = find_files(cwd=str(tmp_path), ext=".py")

    assert result.ok
    assert result.data["files"][0]["path"] == "src/alpha.py"
    assert result.data["backend"] in {"fd", "python"}


def test_find_by_type_uses_fast_backend_when_available(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "alpha.py").write_text("alpha\n", encoding="utf-8")
    (tmp_path / "src" / "beta.txt").write_text("beta\n", encoding="utf-8")

    result = find_by_type(cwd=str(tmp_path), type="python")

    assert result.ok
    assert [item["path"] for item in result.data["files"]] == ["src/alpha.py"]
    assert result.data["backend"] in {"fd", "python"}


def test_read_file_reports_backend_and_line_range(tmp_path: Path) -> None:
    file = tmp_path / "sample.txt"
    file.write_text("one\ntwo\nthree\n", encoding="utf-8")

    result = read_file(cwd=str(tmp_path), file="sample.txt", lines="2-2")

    assert result.ok
    assert result.data["total_lines"] == 3
    assert result.data["content"] == "two\n"
    assert result.data["backend"] in {"bat", "python"}


def test_search_replace_is_preview_by_default(tmp_path: Path) -> None:
    file = tmp_path / "sample.txt"
    file.write_text("before before\n", encoding="utf-8")

    result = search_replace(
        cwd=str(tmp_path),
        pattern="before",
        replacement="after",
        dry_run=True,
    )

    assert result.ok
    assert result.data["total_replacements"] == 2
    assert file.read_text(encoding="utf-8") == "before before\n"


def test_grep_returns_structured_matches(tmp_path: Path) -> None:
    file = tmp_path / "sample.txt"
    file.write_text("before\nmatch\nafter\n", encoding="utf-8")

    result = grep(cwd=str(tmp_path), pattern="match", context=1)

    assert result.ok
    assert any(item["line"] == 2 for item in result.data["matches"])
    assert result.data["backend"] in {"rg-json", "rg", "grep"}
    assert any(item["kind"] in {"match", "context"} for item in result.data["matches"])


def test_grep_can_use_pcre2_and_tracked_files(tmp_path: Path) -> None:
    file = tmp_path / "sample.py"
    file.write_text("value = 'Match'\n", encoding="utf-8")
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "sample.py"], cwd=tmp_path, check=True, capture_output=True)

    tracked = grep(
        cwd=str(tmp_path),
        pattern="match",
        ignore_case=True,
        tracked_only=True,
    )
    pcre = grep(cwd=str(tmp_path), pattern="(?i)match", file_type="py", use_pcre2=True)

    assert tracked.ok and tracked.data["backend"] == "git-grep"
    assert pcre.ok and pcre.data["backend"] == "rg-json"
    assert tracked.data["match_count"] == pcre.data["match_count"] == 1


def test_disk_usage_returns_aggregated_root_size(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "payload.bin").write_bytes(b"x" * 128)

    result = disk_usage(cwd=str(tmp_path), max_entries=20, apparent_size=True)

    assert result.ok
    assert result.data["total_size_bytes"] >= 128
    assert result.data["backend"] in {"ncdu", "python"}
