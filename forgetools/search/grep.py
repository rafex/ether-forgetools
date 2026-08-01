"""forgetools.search.grep - Structured search using rg JSON or git grep."""
from __future__ import annotations

import argparse
import json
import re
import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "search.grep"
DEFAULT_EXCLUDE = (".git", "node_modules", "target", "__pycache__")


def run(
    *,
    cwd: str | None = None,
    pattern: str,
    path: str = ".",
    file_ext: str | None = None,
    file_type: str | None = None,
    context: int = 0,
    ignore_case: bool = False,
    max_results: int = 200,
    tracked_only: bool = False,
    include_hidden: bool = True,
    respect_ignore: bool = True,
    use_pcre2: bool = False,
) -> ForgeResult:
    """Search source files with structured match/context events and backend metadata."""
    with Timer() as t:
        try:
            backend, cmd = _build_command(
                cwd=cwd,
                pattern=pattern,
                path=path,
                file_ext=file_ext,
                file_type=file_type,
                context=context,
                ignore_case=ignore_case,
                max_results=max_results,
                tracked_only=tracked_only,
                include_hidden=include_hidden,
                respect_ignore=respect_ignore,
                use_pcre2=use_pcre2,
            )
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=120)
        except (FileNotFoundError, OSError) as exc:
            return ForgeResult.failure(
                TOOL,
                [str(exc)],
                duration_ms=t.elapsed_ms,
                suggestion="Install ripgrep (rg) or git",
            )
        except ValueError as exc:
            return ForgeResult.failure(TOOL, [str(exc)], duration_ms=t.elapsed_ms)

        # rg and git grep use exit code 1 to mean that there were no matches.
        if rc > 1:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"{backend} exited with code {rc}"],
                duration_ms=t.elapsed_ms,
            )

        if backend == "rg-json":
            matches, stats = _parse_rg_json(stdout, max_results)
        else:
            matches = _parse_text(stdout, max_results)
            stats = None
        data = {
            "pattern": pattern,
            "match_count": len(matches),
            "matches": matches,
            "backend": backend,
            "tracked_only": tracked_only and backend == "git-grep",
        }
        if stats is not None:
            data["stats"] = stats
        return ForgeResult.success(TOOL, data, t.elapsed_ms)


def _build_command(
    *,
    cwd: str | None,
    pattern: str,
    path: str,
    file_ext: str | None,
    file_type: str | None,
    context: int,
    ignore_case: bool,
    max_results: int,
    tracked_only: bool,
    include_hidden: bool,
    respect_ignore: bool,
    use_pcre2: bool,
) -> tuple[str, list[str]]:
    if context < 0:
        raise ValueError("context must be zero or greater")
    if max_results < 1:
        raise ValueError("max_results must be greater than zero")
    if file_ext and not file_ext.startswith("."):
        file_ext = f".{file_ext}"

    if tracked_only and shutil.which("git") and _is_git_repo(cwd):
        cmd = ["git", "grep", "--no-color", "--line-number", "-I"]
        if ignore_case:
            cmd.append("--ignore-case")
        if context:
            cmd += [f"-C{context}"]
        cmd.append(pattern)
        if path and path != ".":
            cmd += ["--", path]
        return "git-grep", cmd

    if not shutil.which("rg"):
        cmd = ["grep", "-rn", "--color=never"]
        if ignore_case:
            cmd.append("-i")
        if context:
            cmd.append(f"-C{context}")
        if file_ext:
            cmd += ["--include", f"*{file_ext}"]
        return "grep", [*cmd, "--", pattern, path]

    cmd = ["rg", "--json"]
    if include_hidden:
        cmd.append("--hidden")
    if not respect_ignore:
        cmd.append("--no-ignore-vcs")
    if ignore_case:
        cmd.append("--ignore-case")
    if use_pcre2:
        cmd.append("--pcre2")
    if context:
        cmd += ["--context", str(context)]
    if file_ext:
        cmd += ["--glob", f"*{file_ext}"]
    if file_type:
        cmd += ["--type", file_type]
    for excluded in DEFAULT_EXCLUDE:
        cmd += ["--glob", f"!{excluded}/**"]
    # Limit output at the engine as well as in the parser. The parser still
    # enforces a global result limit because rg's --max-count is per file.
    cmd += ["--max-count", str(max_results), "--", pattern, path]
    return "rg-json", cmd


def _is_git_repo(cwd: str | None) -> bool:
    rc, _, _ = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=cwd, timeout=10)
    return rc == 0


def _parse_rg_json(stdout: str, max_results: int) -> tuple[list[dict], dict | None]:
    matches: list[dict] = []
    stats: dict | None = None
    for line in stdout.splitlines():
        if len(matches) >= max_results:
            break
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        payload = event.get("data") or {}
        if event_type in {"match", "context"}:
            path = ((payload.get("path") or {}).get("text"))
            line_number = payload.get("line_number")
            text = ((payload.get("lines") or {}).get("text", "")).rstrip("\n")
            matches.append({
                "file": path,
                "line": line_number,
                "text": text,
                "kind": event_type,
            })
        elif event_type == "end":
            stats = payload.get("stats") or None
    return matches, stats


def _parse_text(stdout: str, max_results: int) -> list[dict]:
    matches: list[dict] = []
    for line in stdout.splitlines():
        if len(matches) >= max_results:
            break
        if line == "--":
            continue
        match = re.match(r"^(.+?):(\d+):(.*)", line)
        if not match:
            match = re.match(r"^(.+?)-(\d+)-(.*)", line)
        if match:
            matches.append({
                "file": match.group(1),
                "line": int(match.group(2)),
                "text": match.group(3),
                "kind": "match",
            })
        else:
            matches.append({"file": None, "line": None, "text": line, "kind": "context"})
    return matches


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pattern", required=True)
    p.add_argument("--path", default=".")
    p.add_argument("--file-ext", default=None)
    p.add_argument("--file-type", default=None, help="ripgrep type, e.g. py, rust, js")
    p.add_argument("--context", type=int, default=0)
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--max-results", type=int, default=200)
    p.add_argument("--tracked-only", action="store_true", help="Use git grep for tracked files")
    p.add_argument("--no-hidden", dest="include_hidden", action="store_false", default=True)
    p.add_argument("--no-respect-ignore", dest="respect_ignore", action="store_false", default=True)
    p.add_argument("--pcre2", dest="use_pcre2", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "Search files with rg JSON, git grep, or grep fallback", run, _add_args)
