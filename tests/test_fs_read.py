from forgetools.fs.read import run


def test_fs_read_accepts_file_aliases(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_text("first\nsecond\n", encoding="utf-8")

    for kwargs in (
        {"file": "sample.txt"},
        {"filePath": "sample.txt"},
        {"path": "sample.txt"},
    ):
        result = run(cwd=str(tmp_path), **kwargs)

        assert result.ok is True
        assert result.data["file"] == "sample.txt"
        assert result.data["content"] == "first\nsecond\n"


def test_fs_read_requires_a_file_location():
    result = run()

    assert result.ok is False
    assert result.errors == ["One of 'file', 'filePath', or 'path' is required"]
