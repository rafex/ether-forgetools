from __future__ import annotations

import json
from pathlib import Path

from forgetools.specnative import artifacts, upstream


def test_upstream_install_is_preview_by_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(upstream, "_latest_version", lambda: "v0.9.0")

    result = upstream.run(action="install", target=str(tmp_path))

    assert result.ok
    assert result.data["executed"] is False
    assert result.data["version"] == "v0.9.0"
    assert "--profile" in result.data["command"]


def test_upstream_fetch_returns_document(monkeypatch) -> None:
    monkeypatch.setattr(upstream, "_fetch", lambda url, accept="text/plain": "# SpecNative")

    result = upstream.run(action="fetch", document="readme-es")

    assert result.ok
    assert result.data["content"] == "# SpecNative"
    assert result.data["document"] == "readme-es"


def test_artifact_logging_previews_and_writes_modern_layout(tmp_path: Path) -> None:
    (tmp_path / "spec-native" / "architecture").mkdir(parents=True)

    preview = artifacts.run(
        action="log-architecture",
        title="Use a bounded context",
        context="The system has separate domains.",
        design="Keep domain APIs isolated.",
        consequences="Cross-domain calls use explicit contracts.",
        repo=str(tmp_path),
    )
    assert preview.ok
    assert preview.data["written"] is False
    assert not list((tmp_path / "spec-native" / "architecture").glob("ARCH-*.md"))

    written = artifacts.run(
        action="log-architecture",
        title="Use a bounded context",
        context="The system has separate domains.",
        design="Keep domain APIs isolated.",
        consequences="Cross-domain calls use explicit contracts.",
        repo=str(tmp_path),
        write=True,
    )
    assert written.ok
    path = tmp_path / written.data["path"]
    assert path.exists()
    assert "ARCH-0001" in path.read_text(encoding="utf-8")
