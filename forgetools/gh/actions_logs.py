from __future__ import annotations

"""
gh/actions_logs.py — Get logs from GitHub Actions workflow runs (requires gh CLI + auth).

Actions:
    run     — full logs for a workflow run (all jobs)
    job     — logs for a specific job within a run
    failed  — only the failed steps across all jobs in a run
    tail    — last N lines of a run's logs
    jobs    — list jobs in a run with their status and duration
"""

import argparse
import json
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "gh.actions_logs"


def _gh(*args: str, cwd: str | None = None, timeout: int = 60) -> tuple[int, str, str]:
    return run_command(["gh", *args], cwd=cwd, timeout=timeout)


def _parse_log_sections(raw: str) -> list[dict]:
    """Split raw log output into per-job sections."""
    sections: list[dict] = []
    current: dict | None = None

    for line in raw.splitlines():
        # GitHub log format: YYYY-MM-DDTHH:MM:SS.MMMZ <job> <step> <text>
        # or just raw text
        if line.startswith("\x1b"):
            line = re.sub(r"\x1b\[[0-9;]*m", "", line)  # strip ANSI

        stripped = line.strip()
        if not stripped:
            continue

        # Detect job header line patterns like "##[group]<jobname>"
        if stripped.startswith("##[group]"):
            if current:
                sections.append(current)
            current = {"name": stripped[9:], "lines": []}
        elif current:
            current["lines"].append(stripped)
        else:
            if not sections:
                sections.append({"name": "preamble", "lines": []})
            sections[-1]["lines"].append(stripped)

    if current:
        sections.append(current)
    return sections


def run(
    *,
    action:  str = "jobs",
    run_id:  int | None = None,
    job_id:  int | None = None,
    lines:   int = 100,             # for action=tail
    cwd:     str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if not run_id:
            return ForgeResult.failure(TOOL, ["--run-id is required"], t.elapsed_ms)

        if action == "jobs":
            rc, stdout, stderr = _gh(
                "run", "view", str(run_id),
                "--json", "jobs",
                cwd=cwd,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms,
                                           suggestion="Run `gh auth login` if not authenticated")
            data = json.loads(stdout)
            jobs_raw = data.get("jobs") or []
            jobs = []
            for j in jobs_raw:
                steps = j.get("steps") or []
                failed_steps = [s["name"] for s in steps if s.get("conclusion") == "failure"]
                duration_s = None
                if j.get("startedAt") and j.get("completedAt"):
                    from datetime import datetime, timezone
                    try:
                        fmt = "%Y-%m-%dT%H:%M:%SZ"
                        start = datetime.strptime(j["startedAt"], fmt).replace(tzinfo=timezone.utc)
                        end   = datetime.strptime(j["completedAt"], fmt).replace(tzinfo=timezone.utc)
                        duration_s = int((end - start).total_seconds())
                    except Exception:
                        pass
                jobs.append({
                    "id":           j.get("databaseId"),
                    "name":         j.get("name"),
                    "status":       j.get("status"),
                    "conclusion":   j.get("conclusion"),
                    "started_at":   j.get("startedAt"),
                    "completed_at": j.get("completedAt"),
                    "duration_s":   duration_s,
                    "steps_count":  len(steps),
                    "failed_steps": failed_steps,
                    "url":          j.get("url"),
                })
            failed_count = sum(1 for j in jobs if j.get("conclusion") == "failure")
            return ForgeResult.success(TOOL, {
                "run_id":       run_id,
                "job_count":    len(jobs),
                "failed_count": failed_count,
                "jobs":         jobs,
            }, t.elapsed_ms)

        if action == "run":
            rc, stdout, stderr = _gh("run", "view", "--log", str(run_id), cwd=cwd, timeout=120)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {
                "run_id":   run_id,
                "log_size": len(stdout),
                "log":      stdout,
            }, t.elapsed_ms)

        if action == "job":
            if not job_id:
                return ForgeResult.failure(TOOL, ["--job-id is required for action=job"], t.elapsed_ms)
            rc, stdout, stderr = _gh("run", "view", "--log", "--job", str(job_id), cwd=cwd, timeout=60)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {
                "run_id":   run_id,
                "job_id":   job_id,
                "log_size": len(stdout),
                "log":      stdout,
            }, t.elapsed_ms)

        if action == "failed":
            rc, stdout, stderr = _gh("run", "view", "--log-failed", str(run_id), cwd=cwd, timeout=60)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            log_lines = stdout.splitlines()
            # Try to identify error patterns
            errors = [l for l in log_lines if re.search(r"error|Error|FAILED|FAIL|Exception|fatal", l)]
            return ForgeResult.success(TOOL, {
                "run_id":      run_id,
                "log_lines":   len(log_lines),
                "error_hints": errors[:50],
                "log":         stdout,
            }, t.elapsed_ms)

        if action == "tail":
            rc, stdout, stderr = _gh("run", "view", "--log", str(run_id), cwd=cwd, timeout=120)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            all_lines = stdout.splitlines()
            tail = all_lines[-lines:]
            return ForgeResult.success(TOOL, {
                "run_id":      run_id,
                "total_lines": len(all_lines),
                "tail_lines":  len(tail),
                "log":         "\n".join(tail),
            }, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: jobs | run | job | failed | tail"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action",  default="jobs",
                   choices=["jobs", "run", "job", "failed", "tail"])
    p.add_argument("--run-id",  type=int, default=None, dest="run_id", help="Workflow run ID (required)")
    p.add_argument("--job-id",  type=int, default=None, dest="job_id", help="Job ID for action=job")
    p.add_argument("--lines",   type=int, default=100, help="Lines for action=tail (default: 100)")
    p.add_argument("--cwd",     default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Get GitHub Actions workflow run logs (requires gh auth)", run, _add_args)
