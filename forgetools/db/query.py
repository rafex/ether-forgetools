"""forgetools.db.query — Run a SQL query against sqlite, postgres, or mysql."""
from __future__ import annotations

import argparse
import csv
import io
import json
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "db.query"

_SUGGESTION = "Check connection string format: sqlite=path, postgres=postgresql://user:pass@host/db"


def run(
    *,
    sql: str,
    db: str = "sqlite",
    connection: str = "app.db",
    cwd: str | None = None,
    limit: int = 100,
) -> ForgeResult:
    with Timer() as t:
        sql_to_run = _maybe_add_limit(sql, limit)
        try:
            if db == "sqlite":
                rc, stdout, stderr = run_command(
                    ["sqlite3", "-json", connection, sql_to_run], cwd=cwd
                )
            elif db == "postgres":
                rc, stdout, stderr = run_command(
                    ["psql", connection, "-t", "-A", "--csv", "-c", sql_to_run], cwd=cwd
                )
            elif db == "mysql":
                rc, stdout, stderr = run_command(
                    ["mysql", connection, "-e", sql_to_run, "--batch", "--silent"], cwd=cwd
                )
            else:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unsupported db type: {db}. Use sqlite, postgres, or mysql"],
                    duration_ms=t.elapsed_ms,
                    suggestion=_SUGGESTION,
                )
        except FileNotFoundError:
            return ForgeResult.failure(
                TOOL,
                [f"{db} client not found"],
                duration_ms=t.elapsed_ms,
                suggestion=_SUGGESTION,
            )
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"{db} query failed"],
                duration_ms=t.elapsed_ms,
                suggestion=_SUGGESTION,
            )
        rows, columns = _parse(stdout, db)
        return ForgeResult.success(
            TOOL, {"rows": rows, "count": len(rows), "columns": columns, "db": db}, t.elapsed_ms
        )


def _maybe_add_limit(sql: str, limit: int) -> str:
    stripped = sql.strip().rstrip(";")
    if re.match(r"(?i)\s*select\b", stripped) and not re.search(r"(?i)\blimit\b", stripped):
        return f"{stripped} LIMIT {limit}"
    return sql


def _parse(output: str, db: str) -> tuple[list[dict], list[str]]:
    if db == "sqlite":
        if not output.strip():
            return [], []
        data = json.loads(output)
        columns = list(data[0].keys()) if data else []
        return data, columns
    elif db == "postgres":
        reader = csv.DictReader(io.StringIO(output.strip()))
        rows = list(reader)
        columns = list(reader.fieldnames) if reader.fieldnames else []
        return rows, columns
    else:  # mysql TSV
        lines = output.strip().splitlines()
        if not lines:
            return [], []
        columns = lines[0].split("\t")
        rows = [dict(zip(columns, line.split("\t"))) for line in lines[1:]]
        return rows, columns


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--sql", required=True, help="SQL query to run")
    p.add_argument("--db", default="sqlite", choices=["sqlite", "postgres", "mysql"])
    p.add_argument("--connection", default="app.db", help="Connection string or path")
    p.add_argument("--limit", type=int, default=100, help="Auto-added LIMIT for SELECT queries")


if __name__ == "__main__":
    make_cli(TOOL, "Run a SQL query against a database", run, _add_args)
