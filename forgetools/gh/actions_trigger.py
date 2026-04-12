from __future__ import annotations

"""
gh/actions_trigger.py — Trigger, re-run, and cancel GitHub Actions workflow runs.

Requires gh CLI + auth (write access to the repository).

Actions:
    run         — trigger a workflow_dispatch event (manual trigger)
    rerun       — re-run a specific run (all jobs or failed jobs only)
    cancel      — cancel an in-progress run
    watch       — watch a run until it completes (polls every 5s)
    enable      — enable a disabled workflow
    disable     — disable a workflow
    list-workflows — list all workflows in the repo
"""

import argparse
import json
import time

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "gh.actions_trigger"


def _gh(*args: str, cwd: str | None = None, timeout: int = 30) -> tuple[int, str, str]:
    return run_command(["gh", *args], cwd=cwd, timeout=timeout)


def run(
    *,
    action:    str = "list-workflows",
    workflow:  str | None = None,    # workflow file name (e.g. ci.yml) or workflow id
    run_id:    int | None = None,    # run id for rerun/cancel/watch
    ref:       str | None = None,    # branch/tag for workflow_dispatch
    inputs:    str | None = None,    # JSON string of workflow_dispatch inputs
    failed_only: bool = False,       # rerun failed jobs only
    timeout:   int = 300,            # watch timeout in seconds
    cwd:       str | None = None,
) -> ForgeResult:
    with Timer() as t:

        if action == "list-workflows":
            rc, stdout, stderr = _gh(
                "workflow", "list", "--json", "id,name,path,state",
                cwd=cwd,
            )
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms,
                                           suggestion="Run `gh auth login` if not authenticated")
            workflows = json.loads(stdout)
            return ForgeResult.success(TOOL, {"count": len(workflows), "workflows": workflows}, t.elapsed_ms)

        if action == "run":
            if not workflow:
                return ForgeResult.failure(TOOL, ["--workflow is required for action=run"], t.elapsed_ms)
            cmd = ["gh", "workflow", "run", workflow]
            if ref:
                cmd += ["--ref", ref]
            if inputs:
                # inputs is a JSON string: {"key": "value"}
                try:
                    parsed = json.loads(inputs)
                    for k, v in parsed.items():
                        cmd += ["-f", f"{k}={v}"]
                except json.JSONDecodeError:
                    return ForgeResult.failure(TOOL, ["--inputs must be a valid JSON string"], t.elapsed_ms)

            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=30)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms,
                                           suggestion="Ensure the workflow has workflow_dispatch trigger enabled")
            return ForgeResult.success(TOOL, {
                "triggered": True,
                "workflow":  workflow,
                "ref":       ref,
                "inputs":    inputs,
                "output":    (stdout + stderr).strip(),
            }, t.elapsed_ms)

        if action == "rerun":
            if not run_id:
                return ForgeResult.failure(TOOL, ["--run-id is required for action=rerun"], t.elapsed_ms)
            cmd = ["gh", "run", "rerun", str(run_id)]
            if failed_only:
                cmd.append("--failed")
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=30)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {
                "rerun":      True,
                "run_id":     run_id,
                "failed_only": failed_only,
            }, t.elapsed_ms)

        if action == "cancel":
            if not run_id:
                return ForgeResult.failure(TOOL, ["--run-id is required for action=cancel"], t.elapsed_ms)
            rc, stdout, stderr = _gh("run", "cancel", str(run_id), cwd=cwd)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"cancelled": True, "run_id": run_id}, t.elapsed_ms)

        if action == "watch":
            if not run_id:
                return ForgeResult.failure(TOOL, ["--run-id is required for action=watch"], t.elapsed_ms)
            deadline = time.monotonic() + timeout
            poll_interval = 5
            last_status = None

            while time.monotonic() < deadline:
                rc, stdout, stderr = _gh(
                    "run", "view", str(run_id),
                    "--json", "status,conclusion,name,headBranch,url",
                    cwd=cwd,
                )
                if rc != 0:
                    return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
                info = json.loads(stdout)
                status = info.get("status")
                conclusion = info.get("conclusion")

                if status == "completed":
                    return ForgeResult.success(TOOL, {
                        "run_id":     run_id,
                        "status":     status,
                        "conclusion": conclusion,
                        "name":       info.get("name"),
                        "branch":     info.get("headBranch"),
                        "url":        info.get("url"),
                        "ok":         conclusion == "success",
                    }, t.elapsed_ms)

                last_status = status
                time.sleep(poll_interval)

            return ForgeResult.failure(
                TOOL, [f"Timed out after {timeout}s. Last status: {last_status}"],
                t.elapsed_ms,
                suggestion=f"Increase --timeout or check the run at its URL",
            )

        if action == "enable":
            if not workflow:
                return ForgeResult.failure(TOOL, ["--workflow is required for action=enable"], t.elapsed_ms)
            rc, stdout, stderr = _gh("workflow", "enable", workflow, cwd=cwd)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"enabled": True, "workflow": workflow}, t.elapsed_ms)

        if action == "disable":
            if not workflow:
                return ForgeResult.failure(TOOL, ["--workflow is required for action=disable"], t.elapsed_ms)
            rc, stdout, stderr = _gh("workflow", "disable", workflow, cwd=cwd)
            if rc != 0:
                return ForgeResult.failure(TOOL, [stderr.strip()], t.elapsed_ms)
            return ForgeResult.success(TOOL, {"disabled": True, "workflow": workflow}, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: run | rerun | cancel | watch | enable | disable | list-workflows"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="list-workflows",
                   choices=["run", "rerun", "cancel", "watch", "enable", "disable", "list-workflows"])
    p.add_argument("--workflow",  default=None, help="Workflow file name, e.g. ci.yml (for run/enable/disable)")
    p.add_argument("--run-id",    type=int, default=None, dest="run_id",
                   help="Run ID (for rerun/cancel/watch)")
    p.add_argument("--ref",       default=None, help="Branch or tag for workflow_dispatch")
    p.add_argument("--inputs",    default=None, help='JSON string of dispatch inputs: \'{"key":"value"}\'')
    p.add_argument("--failed-only", action="store_true", dest="failed_only",
                   help="Re-run only failed jobs")
    p.add_argument("--timeout",   type=int, default=300, help="Watch timeout in seconds (default: 300)")
    p.add_argument("--cwd",       default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Trigger, re-run and cancel GitHub Actions runs (requires gh auth)", run, _add_args)
