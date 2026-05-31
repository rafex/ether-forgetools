"""forgetools.frontend.assets - Check referenced local assets in HTML/Markdown files."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

ASSET_RE = re.compile(r"""(?:src|href)=["']([^"']+)["']|!\[[^\]]*\]\(([^)]+)\)""")


def run(*, path: str = ".", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        root = Path(cwd or ".").resolve()
        target = (root / path).resolve()
        files = [target] if target.is_file() else list(target.rglob("*"))
        missing = []
        checked = 0
        for file in files:
            if file.suffix.lower() not in {".html", ".htm", ".md", ".mdx"}:
                continue
            text = file.read_text(encoding="utf-8", errors="ignore")
            for match in ASSET_RE.findall(text):
                ref = match[0] or match[1]
                if not ref or ref.startswith(("http://", "https://", "mailto:", "#", "data:")):
                    continue
                checked += 1
                asset = (file.parent / ref.split("#", 1)[0].split("?", 1)[0]).resolve()
                if not asset.exists():
                    missing.append({"file": str(file), "ref": ref})
        return ForgeResult.success("frontend.assets", {"checked": checked, "missing": missing}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".", help="File or directory to scan")


if __name__ == "__main__":
    make_cli("frontend.assets", "Check referenced local assets", run, _args)
