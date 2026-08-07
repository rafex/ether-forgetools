from __future__ import annotations

from pathlib import Path

from forgetools.search.todo import run


def test_todo_search_uses_bounds_and_excludes_dependency_trees(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".opencode" / "worktrees" / "copy").mkdir(parents=True)
    (tmp_path / "src" / "app.py").write_text("# TODO: fix this\n# FIXME: test\n", encoding="utf-8")
    (tmp_path / ".venv" / "lib" / "ignored.py").write_text("# TODO: ignored\n", encoding="utf-8")
    (tmp_path / ".opencode" / "worktrees" / "copy" / "ignored.py").write_text("# TODO: ignored\n", encoding="utf-8")

    result = run(path=str(tmp_path), max_results=1)

    assert result.ok
    assert result.data["count"] == 1
    assert result.data["truncated"] is True
    assert result.data["items"][0]["file"].endswith("src/app.py")


def test_todo_search_supports_cwd_and_extension_filter(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# TODO: python\n", encoding="utf-8")
    (tmp_path / "src" / "notes.txt").write_text("TODO: text\n", encoding="utf-8")

    result = run(cwd=str(tmp_path), path="src", ext=".py")

    assert result.ok
    assert result.data["count"] == 1
    assert result.data["items"][0]["file"] == "app.py"
