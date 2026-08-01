from __future__ import annotations

"""SpecNative context artifact index and reader."""

import argparse
import re
from pathlib import Path
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.specnative._core import _toml_fallback, context_rel, parse_all_toml_blocks, read_file, uses_modern_layout

TOOL = "specnative.artifacts"

_ARTIFACT_DOCS = {
    "decisions": ("DEC", "decisions"),
    "architecture": ("ARCH", "architecture"),
    "conventions": ("CONV", "conventions"),
}


def _section_for_id(text: str, artifact_id: str) -> str | None:
    pattern = re.compile(
        rf"(^##\s+{re.escape(artifact_id)}(?::|\s|-).*?)(?=^##\s+\w+-\d+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _frontmatter_loads(text: str) -> dict[str, Any]:
    match = re.search(r"^\+\+\+\s*\n(.*?)\n\+\+\+", text, re.DOTALL)
    if not match:
        return {}
    raw = match.group(1)
    try:
        try:
            import tomllib
            return tomllib.loads(raw)
        except ImportError:
            return _toml_fallback(raw)
    except Exception:
        return _toml_fallback(raw)


def _tags_from(text: str, meta: dict[str, Any]) -> list[str]:
    tags = meta.get("tags") or meta.get("labels") or []
    if isinstance(tags, str):
        tags = [tags]
    found = {str(tag).strip() for tag in tags if str(tag).strip()}
    found.update(match.group(1) for match in re.finditer(r"#([A-Za-z0-9_.-]+)", text))
    return sorted(found)


def _list_doc(root: Path, document: str, prefix: str, tag: str | None = None) -> dict[str, Any]:
    rel = context_rel(root, document) or f"agents/{document.upper()}.md"
    text = read_file(root, rel)
    if text is None:
        return {"path": rel, "count": 0, "artifacts": [], "missing": True}

    blocks_by_id: dict[str, dict[str, Any]] = {}
    for block in parse_all_toml_blocks(text):
        artifact_id = str(block.get("id", ""))
        if artifact_id.startswith(prefix):
            blocks_by_id[artifact_id] = block

    artifacts: list[dict[str, Any]] = []
    for match in re.finditer(rf"^##\s+({prefix}-\d+)(?::|\s|-)?\s*(.*)$", text, re.MULTILINE):
        artifact_id = match.group(1)
        title = match.group(2).strip()
        section = _section_for_id(text, artifact_id) or ""
        meta = blocks_by_id.get(artifact_id, {})
        tags = _tags_from(section, meta)
        entry = {
            "id": artifact_id,
            "title": meta.get("title") or title,
            "state": meta.get("state"),
            "tags": tags,
            "path": rel,
        }
        if tag and tag not in tags and f"#{tag}" not in section:
            continue
        artifacts.append(entry)

    for artifact_id, meta in blocks_by_id.items():
        if any(item["id"] == artifact_id for item in artifacts):
            continue
        tags = _tags_from("", meta)
        if tag and tag not in tags:
            continue
        artifacts.append(
            {
                "id": artifact_id,
                "title": meta.get("title", ""),
                "state": meta.get("state"),
                "tags": tags,
                "path": rel,
            }
        )
    if uses_modern_layout(root):
        artifact_dir = root / "spec-native" / document
        if artifact_dir.is_dir():
            for path in sorted(artifact_dir.glob(f"{prefix}-*.md")):
                rel_path = str(path.relative_to(root))
                body = path.read_text(encoding="utf-8")
                meta = _frontmatter_loads(body)
                artifact_id = str(meta.get("id") or path.stem)
                tags = _tags_from(body, meta)
                if tag and tag not in tags and f"#{tag}" not in body:
                    continue
                if any(item["id"] == artifact_id for item in artifacts):
                    continue
                artifacts.append(
                    {
                        "id": artifact_id,
                        "title": meta.get("title") or path.stem,
                        "state": meta.get("status") or meta.get("state"),
                        "tags": tags,
                        "path": rel_path,
                    }
                )
    return {"path": rel, "count": len(artifacts), "artifacts": artifacts, "missing": False}


def _read_artifact(root: Path, artifact_id: str) -> dict[str, Any] | None:
    for document, (prefix, _) in _ARTIFACT_DOCS.items():
        if not artifact_id.startswith(prefix):
            continue
        rel = context_rel(root, document) or f"agents/{document.upper()}.md"
        text = read_file(root, rel)
        if text is None:
            return None
        section = _section_for_id(text, artifact_id)
        if section is None and uses_modern_layout(root):
            artifact_dir = root / "spec-native" / document
            if artifact_dir.is_dir():
                for path in sorted(artifact_dir.glob(f"{prefix}-*.md")):
                    body = path.read_text(encoding="utf-8")
                    meta = _frontmatter_loads(body)
                    if meta.get("id") == artifact_id or path.stem.startswith(artifact_id):
                        return {
                            "id": artifact_id,
                            "document": document,
                            "path": str(path.relative_to(root)),
                            "content": body,
                            "found": True,
                        }
        return {"id": artifact_id, "document": document, "path": rel, "content": section, "found": section is not None}
    return None


def run(
    *,
    action: str = "list-decisions",
    id: str | None = None,
    tag: str | None = None,
    repo: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    """List or read SpecNative persistent context artifacts."""
    with Timer() as t:
        root = Path(repo or cwd or ".").resolve()
        if not root.is_dir():
            return ForgeResult.failure(TOOL, [f"Directory not found: {root}"], t.elapsed_ms)

        list_actions = {
            "list-decisions": ("DEC", "decisions"),
            "list-architecture": ("ARCH", "architecture"),
            "list-conventions": ("CONV", "conventions"),
        }
        if action in list_actions:
            prefix, document = list_actions[action]
            return ForgeResult.success(TOOL, {"action": action, **_list_doc(root, document, prefix, tag)}, t.elapsed_ms)
        if action == "read":
            if not id:
                return ForgeResult.failure(TOOL, ["id is required for action=read"], t.elapsed_ms)
            artifact = _read_artifact(root, id)
            if not artifact:
                return ForgeResult.failure(TOOL, [f"Unsupported artifact id: {id}"], t.elapsed_ms)
            if not artifact["found"]:
                return ForgeResult.failure(TOOL, [f"Artifact not found: {id}"], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"action": action, **artifact}, t.elapsed_ms)
        return ForgeResult.failure(
            TOOL,
            ["Unknown action. Use: list-decisions | list-architecture | list-conventions | read"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="list-decisions", choices=["list-decisions", "list-architecture", "list-conventions", "read"])
    p.add_argument("--id", default=None)
    p.add_argument("--tag", default=None)
    p.add_argument("--repo", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "List or read SpecNative context artifacts", run, _add_args)
