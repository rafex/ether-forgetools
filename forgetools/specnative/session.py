from __future__ import annotations

"""SpecNative multi-agent session continuity tools."""

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.specnative._core import _toml_loads, context_rel, read_file

TOOL = "specnative.session"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _session_path(root: Path) -> Path:
    rel = context_rel(root, "session") or "spec-native/SESSION.md"
    return root / rel


def _session_template(fields: dict[str, str], sections: dict[str, str]) -> str:
    meta = "[session]\n" + "\n".join(f'{k} = "{v}"' for k, v in fields.items())
    parts = [f"+++\n{meta}\n+++\n\n# Active Session\n"]
    for heading, content in sections.items():
        parts.append(f"\n## {heading}\n\n{content.rstrip()}\n")
    return "".join(parts)


def _extract_sections(text: str) -> dict[str, str]:
    body_match = re.search(r"\+\+\+.*?\+\+\+(.*)", text, re.DOTALL)
    body = body_match.group(1) if body_match else text
    sections: dict[str, str] = {}
    for match in re.finditer(r"^##\s+(.+?)\s*$\n(.*?)(?=^##\s|\Z)", body, re.MULTILINE | re.DOTALL):
        content = match.group(2).strip()
        if content and not content.startswith("<!--"):
            sections[match.group(1).strip()] = content
    return sections


def run(
    *,
    action: str = "resume",
    initiative: str | None = None,
    task_id: str | None = None,
    intent: str | None = None,
    next_steps: str | None = None,
    context_notes: str = "",
    agent_name: str = "",
    write: bool = False,
    repo: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        root = Path(repo or cwd or ".").resolve()
        if not root.is_dir():
            return ForgeResult.failure(TOOL, [f"Directory not found: {root}"], t.elapsed_ms)

        path = _session_path(root)

        if action == "resume":
            text = read_file(root, str(path.relative_to(root)))
            if text is None:
                return ForgeResult.success(TOOL, {
                    "state": "missing",
                    "message": "No SESSION.md found. Start fresh or run specnative project --action health-check.",
                    "path": str(path),
                }, t.elapsed_ms)

            meta = _toml_loads(text)
            session = meta.get("session", meta)
            state = session.get("state", "idle")
            sections = _extract_sections(text)
            suggestions = ["specnative_status(action='status')"]
            current_initiative = session.get("initiative") or initiative
            current_task = session.get("task") or task_id
            if current_initiative:
                suggestions.append(f"specnative_context(action='list-tasks', initiative='{current_initiative}')")
                suggestions.append(f"specnative_context(action='read-spec', initiative='{current_initiative}')")
            if current_initiative and current_task:
                suggestions.append(
                    f"specnative_session(action='checkpoint', initiative='{current_initiative}', task_id='{current_task}', ...)"
                )

            return ForgeResult.success(TOOL, {
                "action": "resume",
                "path": str(path),
                "state": state,
                "session": session,
                "sections": sections,
                "suggested_next_actions": suggestions,
            }, t.elapsed_ms)

        if action == "checkpoint":
            missing = [
                name for name, value in {
                    "initiative": initiative,
                    "task_id": task_id,
                    "intent": intent,
                    "next_steps": next_steps,
                }.items()
                if not value
            ]
            if missing:
                return ForgeResult.failure(TOOL, [f"Missing required fields: {', '.join(missing)}"], t.elapsed_ms)

            fields = {
                "state": "in_progress",
                "agent": agent_name or "unknown",
                "initiative": initiative or "",
                "task": task_id or "",
                "intent": intent or "",
                "last_updated": _now_iso(),
            }
            sections = {
                "Current state": intent or "",
                "Next steps": next_steps or "",
            }
            if context_notes:
                sections["Context for next agent"] = context_notes
            content = _session_template(fields, sections)
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return ForgeResult.success(TOOL, {
                "action": "checkpoint",
                "written": write,
                "path": str(path),
                "content": None if write else content,
            }, t.elapsed_ms)

        if action == "clear":
            content = _session_template(
                {
                    "state": "idle",
                    "agent": agent_name or "",
                    "initiative": "",
                    "task": "",
                    "intent": "",
                    "last_updated": _now_iso(),
                },
                {
                    "Current state": "No active work.",
                    "Next steps": "Run specnative status or suggest-next.",
                },
            )
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return ForgeResult.success(TOOL, {
                "action": "clear",
                "written": write,
                "path": str(path),
                "content": None if write else content,
            }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: resume | checkpoint | clear"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="resume", choices=["resume", "checkpoint", "clear"])
    p.add_argument("--initiative", default=None)
    p.add_argument("--task-id", dest="task_id", default=None)
    p.add_argument("--intent", default=None)
    p.add_argument("--next-steps", dest="next_steps", default=None)
    p.add_argument("--context-notes", default="")
    p.add_argument("--agent-name", default="")
    p.add_argument("--write", action="store_true")
    p.add_argument("--repo", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "SpecNative multi-agent session continuity", run, _add_args)
