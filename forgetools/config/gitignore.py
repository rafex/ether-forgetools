"""forgetools.config.gitignore — Manage .gitignore patterns for common presets."""
from __future__ import annotations

import argparse
import os

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "config.gitignore"

_PRESETS: dict[str, dict[str, list[str]]] = {
    "macos": {
        "header": "# macOS metadata files",
        "lines": [
            "._*",
            ".DS_Store",
            ".AppleDouble/",
            ".LSOverride",
            ".Spotlight-V100",
            ".Trashes",
        ],
    },
    "claude": {
        "header": "# Claude Code — ignorar todo excepto config compartida",
        "lines": [
            ".claude/",
            "!.claude/launch.json",
            "!.claude/settings.json",
            "!.claude/CLAUDE.md",
        ],
    },
}


def run(
    *,
    cwd: str | None = None,
    preset: str = "all",
    dry_run: bool = False,
) -> ForgeResult:
    """Add common .gitignore patterns for macOS and/or Claude Code.

    Presets: macos | claude | all (default)
    Use dry_run=True to preview changes without writing.
    """
    with Timer() as t:
        root = cwd or os.getcwd()
        gitignore_path = os.path.join(root, ".gitignore")

        valid_presets = {"macos", "claude", "all"}
        if preset not in valid_presets:
            return ForgeResult.failure(
                TOOL,
                [f"Unknown preset '{preset}'. Valid: {', '.join(sorted(valid_presets))}"],
                duration_ms=t.elapsed_ms,
            )

        selected = (
            list(_PRESETS.keys()) if preset == "all"
            else [preset]
        )

        existing_lines: set[str] = set()
        current_content = ""
        if os.path.exists(gitignore_path):
            with open(gitignore_path, encoding="utf-8") as f:
                current_content = f.read()
            existing_lines = {ln.strip() for ln in current_content.splitlines()}

        blocks_to_add: list[dict] = []
        for key in selected:
            cfg = _PRESETS[key]
            missing = [ln for ln in cfg["lines"] if ln not in existing_lines]
            if missing:
                blocks_to_add.append({"preset": key, "header": cfg["header"], "lines": missing})

        if not blocks_to_add:
            return ForgeResult.success(
                TOOL,
                {"path": gitignore_path, "added": [], "message": "Nothing to add — all patterns already present"},
                t.elapsed_ms,
            )

        new_block = "\n"
        for block in blocks_to_add:
            new_block += f"\n{block['header']}\n"
            new_block += "\n".join(block["lines"]) + "\n"

        if not dry_run:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write(new_block)

        added_summary = [
            {"preset": b["preset"], "lines": b["lines"]}
            for b in blocks_to_add
        ]

        return ForgeResult.success(
            TOOL,
            {
                "path": gitignore_path,
                "dry_run": dry_run,
                "added": added_summary,
                "preview": new_block.strip(),
            },
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--preset",
        default="all",
        choices=["macos", "claude", "all"],
        help="Pattern set to add (default: all)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing",
    )


if __name__ == "__main__":
    make_cli(TOOL, "Add .gitignore patterns for macOS and Claude Code", run, _add_args)
