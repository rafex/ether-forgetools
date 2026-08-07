from __future__ import annotations

"""SpecNative context artifact index and reader."""

import argparse
import re
from datetime import datetime, timezone
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


def _next_artifact_id(root: Path, prefix: str) -> str:
    values: list[int] = []
    for path in root.rglob("*.md"):
        if ".git" in path.parts:
            continue
        values.extend(int(value) for value in re.findall(rf"{prefix}-(\d+)", path.read_text(encoding="utf-8", errors="ignore")))
    return f"{prefix}-{max(values, default=0) + 1:04d}"


def _artifact_content(
    artifact_id: str,
    title: str,
    fields: dict[str, str],
    body: str,
    owner: str,
    tags: list[str] | None,
) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "+++",
        f'kind = "context_artifact"',
        f'id = "{artifact_id}"',
        f'title = "{title.replace(chr(34), chr(39))}"',
        f'owner = "{owner}"',
        f'created_at = "{today}"',
        f'updated_at = "{today}"',
        f"tags = [{', '.join(chr(34) + tag.replace(chr(34), chr(39)) + chr(34) for tag in (tags or []))}]",
        "+++",
        "",
        f"# {artifact_id}: {title}",
        "",
    ]
    for key, value in fields.items():
        lines.extend([f"## {key.title()}", "", value.strip(), ""])
    lines.extend([body.strip(), ""])
    return "\n".join(lines)


def _write_artifact(
    root: Path,
    *,
    document: str,
    prefix: str,
    title: str,
    fields: dict[str, str],
    body: str,
    owner: str,
    tags: list[str] | None,
    write: bool,
) -> dict[str, Any]:
    artifact_id = _next_artifact_id(root, prefix)
    content = _artifact_content(artifact_id, title, fields, body, owner, tags)
    if uses_modern_layout(root):
        path = root / "spec-native" / document / f"{artifact_id}.md"
    else:
        path = root / "agents" / f"{document.upper()}.md"
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        if uses_modern_layout(root):
            path.write_text(content, encoding="utf-8")
        else:
            existing = path.read_text(encoding="utf-8") if path.exists() else f"# {document.upper()}\n"
            path.write_text(existing.rstrip() + "\n\n" + content, encoding="utf-8")
    return {
        "id": artifact_id,
        "document": document,
        "path": str(path.relative_to(root)),
        "written": write,
        "content": None if write else content,
    }


def run(
    *,
    action: str = "list-decisions",
    id: str | None = None,
    tag: str | None = None,
    title: str | None = None,
    context: str = "",
    design: str = "",
    rationale: str = "",
    rule: str = "",
    consequences: str = "",
    owner: str = "team",
    tags: list[str] | None = None,
    write: bool = False,
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
        if action == "log-architecture":
            missing = [name for name, value in {"title": title, "context": context, "design": design, "consequences": consequences}.items() if not value]
            if missing:
                return ForgeResult.failure(TOOL, [f"Missing required fields: {', '.join(missing)}"], t.elapsed_ms)
            data = _write_artifact(
                root, document="architecture", prefix="ARCH", title=title or "",
                fields={"Context": context, "Design": design, "Consequences": consequences},
                body="", owner=owner, tags=tags, write=write,
            )
            return ForgeResult.success(TOOL, {"action": action, **data}, t.elapsed_ms)
        if action == "log-convention":
            missing = [name for name, value in {"title": title, "rationale": rationale, "rule": rule, "consequences": consequences}.items() if not value]
            if missing:
                return ForgeResult.failure(TOOL, [f"Missing required fields: {', '.join(missing)}"], t.elapsed_ms)
            data = _write_artifact(
                root, document="conventions", prefix="CONV", title=title or "",
                fields={"Rationale": rationale, "Rule": rule, "Consequences": consequences},
                body="", owner=owner, tags=tags, write=write,
            )
            return ForgeResult.success(TOOL, {"action": action, **data}, t.elapsed_ms)
        return ForgeResult.failure(
            TOOL,
            ["Unknown action. Use: list-decisions | list-architecture | list-conventions | read | log-architecture | log-convention"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="list-decisions", choices=["list-decisions", "list-architecture", "list-conventions", "read", "log-architecture", "log-convention"])
    p.add_argument("--id", default=None)
    p.add_argument("--tag", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--context", default="")
    p.add_argument("--design", default="")
    p.add_argument("--rationale", default="")
    p.add_argument("--rule", default="")
    p.add_argument("--consequences", default="")
    p.add_argument("--owner", default="team")
    p.add_argument("--tags", nargs="*", default=None)
    p.add_argument("--write", action="store_true")
    p.add_argument("--repo", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "List or read SpecNative context artifacts", run, _add_args)
