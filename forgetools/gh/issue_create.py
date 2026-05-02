from __future__ import annotations

"""
gh/issue_create.py — Create and manage GitHub issues (requires gh CLI + auth).

Actions:
    create  — open a new issue with title, body, labels, assignees, milestone
    close   — close an existing issue
    reopen  — reopen a closed issue
    comment — add a comment to an issue
    edit    — edit title, body, labels, or assignees of an issue
    pin     — pin an issue (requires maintainer)
"""

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "gh.issue_create"


def _gh(*args: str, cwd: str | None = None) -> tuple[int, str, str]:
    return run_command(["gh", *args], cwd=cwd, timeout=30)


def run(
    *,
    action:     str = "create",
    title:      str | None = None,
    body:       str | None = None,
    body_file:  str | None = None,
    labels:     str | None = None,      # comma-separated
    assignees:  str | None = None,      # comma-separated
    milestone:  str | None = None,
    number:     int | None = None,      # issue number for close/reopen/comment/edit
    comment:    str | None = None,      # comment body for action=comment
    project:    str | None = None,
    web:        bool = False,
    cwd:        str | None = None,
) -> ForgeResult:
    with Timer() as t:

        # ── create ────────────────────────────────────────────────────────
        if action == "create":
            if not title:
                return ForgeResult.failure(TOOL, ["--title is required for action=create"], t.elapsed_ms)
            cmd = ["gh", "issue", "create", "--title", title]
            if body:
                cmd += ["--body", body]
            elif body_file:
                cmd += ["--body-file", body_file]
            else:
                cmd += ["--body", ""]
            if labels:
                for lbl in labels.split(","):
                    cmd += ["--label", lbl.strip()]
            if assignees:
                for a in assignees.split(","):
                    cmd += ["--assignee", a.strip()]
            if milestone:
                cmd += ["--milestone", milestone]
            if project:
                cmd += ["--project", project]
            if web:
                cmd.append("--web")

            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=30)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip() or f"gh issue create failed (rc={rc})"],
                                           t.elapsed_ms,
                                           suggestion="Run `gh auth login` if not authenticated")
            # stdout contains the issue URL
            url = stdout.strip()
            number_str = url.rstrip("/").split("/")[-1]
            return ForgeResult.success(TOOL, {
                "created": True,
                "url":     url,
                "number":  int(number_str) if number_str.isdigit() else None,
                "title":   title,
            }, t.elapsed_ms)

        # ── close ─────────────────────────────────────────────────────────
        if action == "close":
            if not number:
                return ForgeResult.failure(TOOL, ["--number is required for action=close"], t.elapsed_ms)
            cmd = ["gh", "issue", "close", str(number)]
            if comment:
                cmd += ["--comment", comment]
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=30)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"closed": True, "number": number}, t.elapsed_ms)

        # ── reopen ────────────────────────────────────────────────────────
        if action == "reopen":
            if not number:
                return ForgeResult.failure(TOOL, ["--number is required for action=reopen"], t.elapsed_ms)
            rc, stdout, stderr = run_command(["gh", "issue", "reopen", str(number)], cwd=cwd, timeout=30)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"reopened": True, "number": number}, t.elapsed_ms)

        # ── comment ───────────────────────────────────────────────────────
        if action == "comment":
            if not number:
                return ForgeResult.failure(TOOL, ["--number is required for action=comment"], t.elapsed_ms)
            if not comment and not body:
                return ForgeResult.failure(TOOL, ["--comment or --body is required for action=comment"], t.elapsed_ms)
            text = comment or body or ""
            rc, stdout, stderr = run_command(
                ["gh", "issue", "comment", str(number), "--body", text],
                cwd=cwd, timeout=30,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"commented": True, "number": number, "url": stdout.strip()}, t.elapsed_ms)

        # ── edit ──────────────────────────────────────────────────────────
        if action == "edit":
            if not number:
                return ForgeResult.failure(TOOL, ["--number is required for action=edit"], t.elapsed_ms)
            cmd = ["gh", "issue", "edit", str(number)]
            if title:
                cmd += ["--title", title]
            if body:
                cmd += ["--body", body]
            if labels:
                cmd += ["--add-label", labels]
            if assignees:
                cmd += ["--add-assignee", assignees]
            if milestone:
                cmd += ["--milestone", milestone]
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=30)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"edited": True, "number": number, "url": stdout.strip()}, t.elapsed_ms)

        # ── pin ───────────────────────────────────────────────────────────
        if action == "pin":
            if not number:
                return ForgeResult.failure(TOOL, ["--number is required for action=pin"], t.elapsed_ms)
            rc, stdout, stderr = run_command(["gh", "issue", "pin", str(number)], cwd=cwd, timeout=30)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"pinned": True, "number": number}, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: create | close | reopen | comment | edit | pin"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="create",
                   choices=["create", "close", "reopen", "comment", "edit", "pin"])
    p.add_argument("--title",      default=None)
    p.add_argument("--body",       default=None)
    p.add_argument("--body-file",  default=None, dest="body_file")
    p.add_argument("--labels",     default=None, help="Comma-separated label names")
    p.add_argument("--assignees",  default=None, help="Comma-separated GitHub usernames")
    p.add_argument("--milestone",  default=None)
    p.add_argument("--number",     type=int, default=None, help="Issue number")
    p.add_argument("--comment",    default=None, help="Comment text")
    p.add_argument("--project",    default=None)
    p.add_argument("--web",        action="store_true")
    p.add_argument("--cwd",        default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Create and manage GitHub issues (requires gh auth)", run, _add_args)
