"""forgetools.db.migrations — Check database migration status."""
from __future__ import annotations

import argparse
import os
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "db.migrations"

_MIGRATION_DIRS = [
    "src/main/resources/db/migration",
    "src/main/resources/db/changelog",
    "migrations",
    "db/migrations",
]


def run(
    *,
    tool: str = "flyway",
    connection: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if tool == "flyway":
            return _flyway(connection, cwd, t)
        elif tool == "liquibase":
            return _liquibase(connection, cwd, t)
        else:
            return ForgeResult.failure(
                TOOL,
                [f"Unsupported tool: {tool}. Use flyway or liquibase"],
                duration_ms=t.elapsed_ms,
            )


def _flyway(connection: str | None, cwd: str | None, t) -> ForgeResult:
    cmd = ["flyway", "info"]
    if connection:
        cmd.append(f"-url={connection}")
    try:
        rc, stdout, stderr = run_command(cmd, cwd=cwd)
    except FileNotFoundError:
        return _file_fallback("flyway", cwd, t)
    if rc != 0:
        return _file_fallback("flyway", cwd, t)
    migrations = _parse_flyway(stdout)
    applied = sum(1 for m in migrations if m["state"] == "applied")
    pending = sum(1 for m in migrations if m["state"] == "pending")
    failed = sum(1 for m in migrations if m["state"] == "failed")
    return ForgeResult.success(TOOL, {
        "tool": "flyway",
        "total": len(migrations),
        "applied": applied,
        "pending": pending,
        "migrations": migrations,
    }, t.elapsed_ms)


def _liquibase(connection: str | None, cwd: str | None, t) -> ForgeResult:
    cmd = ["liquibase", "status", "--verbose"]
    if connection:
        cmd.extend(["--url", connection])
    try:
        rc, stdout, stderr = run_command(cmd, cwd=cwd)
    except FileNotFoundError:
        return _file_fallback("liquibase", cwd, t)
    if rc != 0:
        return _file_fallback("liquibase", cwd, t)
    migrations = _parse_liquibase(stdout + stderr)
    applied = sum(1 for m in migrations if m["state"] == "applied")
    pending = sum(1 for m in migrations if m["state"] == "pending")
    return ForgeResult.success(TOOL, {
        "tool": "liquibase",
        "total": len(migrations),
        "applied": applied,
        "pending": pending,
        "migrations": migrations,
    }, t.elapsed_ms)


def _file_fallback(tool_name: str, cwd: str | None, t) -> ForgeResult:
    base = cwd or os.getcwd()
    migrations = []
    for d in _MIGRATION_DIRS:
        full = os.path.join(base, d)
        if os.path.isdir(full):
            for fname in sorted(os.listdir(full)):
                if fname.endswith(".sql") or fname.endswith(".xml") or fname.endswith(".yaml"):
                    m = re.match(r"V?(\d+[\d_.]*)", fname, re.IGNORECASE)
                    version = m.group(1) if m else fname
                    desc_m = re.match(r"V?[\d_.]+[_]+(.*?)\.(sql|xml|yaml)$", fname, re.IGNORECASE)
                    desc = desc_m.group(1).replace("_", " ") if desc_m else fname
                    migrations.append({
                        "version": version,
                        "description": desc,
                        "state": "pending",
                        "applied_at": None,
                    })
    return ForgeResult.success(TOOL, {
        "tool": tool_name,
        "total": len(migrations),
        "applied": 0,
        "pending": len(migrations),
        "migrations": migrations,
    }, t.elapsed_ms)


def _parse_flyway(output: str) -> list[dict]:
    migrations = []
    in_table = False
    for line in output.splitlines():
        if re.match(r"\s*[-+|]+\s*$", line):
            in_table = True
            continue
        if not in_table:
            continue
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) < 4 or parts[0].lower() in ("version", "+-"):
            continue
        version = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        state_raw = parts[4].lower() if len(parts) > 4 else parts[-1].lower()
        applied_at = parts[3] if len(parts) > 3 else None
        if "success" in state_raw or "applied" in state_raw:
            state = "applied"
        elif "pending" in state_raw:
            state = "pending"
        elif "failed" in state_raw:
            state = "failed"
        else:
            state = "pending"
        migrations.append({
            "version": version,
            "description": description,
            "state": state,
            "applied_at": applied_at if applied_at and applied_at != "" else None,
        })
    return migrations


def _parse_liquibase(output: str) -> list[dict]:
    migrations = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("changeSet"):
            m = re.search(r"changeSet\s+(.+?):", line)
            version = m.group(1) if m else line
            state = "pending" if "not yet" in line.lower() else "applied"
            migrations.append({"version": version, "description": "", "state": state, "applied_at": None})
    return migrations


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--tool", default="flyway", choices=["flyway", "liquibase"])
    p.add_argument("--connection", default=None, help="Database connection URL")


if __name__ == "__main__":
    make_cli(TOOL, "Check database migration status", run, _add_args)
