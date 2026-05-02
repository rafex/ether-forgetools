"""forgetools.fs.diff — Diff two files or git refs."""
from __future__ import annotations

import argparse
import difflib
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "fs.diff"


def run(*, a: str, b: str, cwd: str | None = None, context: int = 3) -> ForgeResult:
    with Timer() as t:
        try:
            if _is_file(a) or _is_file(b):
                diff_text = _file_diff(a, b, context, cwd)
            else:
                diff_text = _git_diff(a, b, context, cwd)
                if diff_text is None:
                    return ForgeResult.failure(TOOL, [f"git diff failed for refs: {a} {b}"], t.elapsed_ms)

            data = _parse_unified_diff(diff_text)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)


def _is_file(ref: str) -> bool:
    return "/" in ref or "." in ref


def _file_diff(a: str, b: str, context: int, cwd: str | None) -> str:
    import os
    base = cwd or "."
    path_a = os.path.join(base, a) if not os.path.isabs(a) else a
    path_b = os.path.join(base, b) if not os.path.isabs(b) else b
    with open(path_a) as fa, open(path_b) as fb:
        lines_a = fa.readlines()
        lines_b = fb.readlines()
    return "".join(difflib.unified_diff(lines_a, lines_b, fromfile=a, tofile=b, n=context))


def _git_diff(a: str, b: str, context: int, cwd: str | None) -> str | None:
    rc, stdout, stderr = run_command(
        ["git", "diff", f"-U{context}", a, b], cwd=cwd
    )
    if rc != 0:
        return None
    return stdout


def _parse_unified_diff(diff_text: str) -> dict:
    files_changed = insertions = deletions = 0
    hunks: list[dict] = []
    current_file: str | None = None
    current_hunk: dict | None = None

    for line in diff_text.splitlines():
        if line.startswith("--- "):
            current_file = line[4:].split("\t")[0].lstrip("a/")
        elif line.startswith("+++ "):
            new_file = line[4:].split("\t")[0].lstrip("b/")
            if current_file and new_file != "/dev/null":
                files_changed += 1
                current_hunk = None
        elif line.startswith("@@ "):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if m:
                current_hunk = {
                    "file": current_file or "",
                    "old_start": int(m.group(1)),
                    "new_start": int(m.group(2)),
                    "lines": [],
                }
                hunks.append(current_hunk)
        elif current_hunk is not None:
            if line.startswith("+") and not line.startswith("+++"):
                current_hunk["lines"].append({"type": "+", "content": line[1:]})
                insertions += 1
            elif line.startswith("-") and not line.startswith("---"):
                current_hunk["lines"].append({"type": "-", "content": line[1:]})
                deletions += 1
            elif line.startswith(" "):
                current_hunk["lines"].append({"type": " ", "content": line[1:]})

    # Group hunks by file
    file_map: dict[str, dict] = {}
    for hunk in hunks:
        fname = hunk["file"]
        if fname not in file_map:
            file_map[fname] = {"file": fname, "hunks": []}
        file_map[fname]["hunks"].append({
            "old_start": hunk["old_start"],
            "new_start": hunk["new_start"],
            "lines": hunk["lines"],
        })

    return {
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
        "hunks": list(file_map.values()),
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--a", required=True, help="First file path or git ref")
    p.add_argument("--b", required=True, help="Second file path or git ref")
    p.add_argument("--context", type=int, default=3, help="Context lines around changes")


if __name__ == "__main__":
    make_cli(TOOL, "Diff two files or git refs", run, _add_args)
