"""forgetools.db.schema — Inspect database schema."""
from __future__ import annotations

import argparse
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "db.schema"

_SUGGESTION = "Check connection string format: sqlite=path, postgres=postgresql://user:pass@host/db"


def run(
    *,
    db: str = "sqlite",
    connection: str = "app.db",
    table: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        try:
            if db == "sqlite":
                result = _sqlite_schema(connection, table, cwd, t)
            elif db == "postgres":
                result = _postgres_schema(connection, table, cwd, t)
            else:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unsupported db type: {db}. Use sqlite or postgres"],
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
        return result


def _sqlite_schema(connection: str, table: str | None, cwd: str | None, t) -> ForgeResult:
    if table:
        rc, stdout, stderr = run_command(
            ["sqlite3", connection, f".schema {table}"], cwd=cwd
        )
    else:
        rc, stdout, stderr = run_command(
            ["sqlite3", connection, ".schema"], cwd=cwd
        )
    if rc != 0:
        return ForgeResult.failure(
            TOOL, [stderr.strip() or "sqlite3 schema failed"],
            duration_ms=t.elapsed_ms, suggestion=_SUGGESTION
        )
    tables = _parse_sqlite_schema(stdout)
    if table:
        tables = [tbl for tbl in tables if tbl["name"] == table]
    return ForgeResult.success(TOOL, {"tables": tables}, t.elapsed_ms)


def _postgres_schema(connection: str, table: str | None, cwd: str | None, t) -> ForgeResult:
    where = "WHERE table_schema='public'"
    if table:
        where += f" AND table_name='{table}'"
    sql = (
        f"SELECT table_name,column_name,data_type,is_nullable,column_default "
        f"FROM information_schema.columns {where} ORDER BY table_name,ordinal_position"
    )
    rc, stdout, stderr = run_command(
        ["psql", connection, "-t", "-A", "-F|", "-c", sql], cwd=cwd
    )
    if rc != 0:
        return ForgeResult.failure(
            TOOL, [stderr.strip() or "psql schema query failed"],
            duration_ms=t.elapsed_ms, suggestion=_SUGGESTION
        )
    tables = _parse_postgres_schema(stdout)
    return ForgeResult.success(TOOL, {"tables": tables}, t.elapsed_ms)


def _parse_sqlite_schema(output: str) -> list[dict]:
    tables: dict[str, list[dict]] = {}
    current_table: str | None = None
    current_lines: list[str] = []

    for line in output.splitlines():
        stripped = line.strip()
        m = re.match(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?[\"']?(\w+)[\"']?\s*\(", stripped, re.IGNORECASE)
        if m:
            current_table = m.group(1)
            current_lines = [line]
            tables[current_table] = []
        elif current_table and stripped.startswith(")"):
            current_lines.append(line)
            tables[current_table] = _parse_sqlite_columns("\n".join(current_lines))
            current_table = None
            current_lines = []
        elif current_table:
            current_lines.append(line)

    return [{"name": name, "columns": cols} for name, cols in tables.items()]


def _parse_sqlite_columns(create_stmt: str) -> list[dict]:
    columns = []
    # Extract the column definitions between the outer parens
    m = re.search(r"\((.+)\)", create_stmt, re.DOTALL)
    if not m:
        return columns
    body = m.group(1)
    for part in body.split(","):
        part = part.strip()
        if not part or re.match(r"(?i)(PRIMARY KEY|UNIQUE|CHECK|FOREIGN KEY|CONSTRAINT)", part):
            continue
        col_m = re.match(r'["\']?(\w+)["\']?\s+(\w+)', part)
        if col_m:
            name, col_type = col_m.group(1), col_m.group(2)
            nullable = "NOT NULL" not in part.upper()
            default_m = re.search(r"DEFAULT\s+(\S+)", part, re.IGNORECASE)
            default = default_m.group(1) if default_m else None
            columns.append({"name": name, "type": col_type, "nullable": nullable, "default": default})
    return columns


def _parse_postgres_schema(output: str) -> list[dict]:
    tables: dict[str, list[dict]] = {}
    for line in output.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 5:
            continue
        tname, cname, dtype, nullable, default = (p.strip() for p in parts[:5])
        if tname not in tables:
            tables[tname] = []
        tables[tname].append({
            "name": cname,
            "type": dtype,
            "nullable": nullable.upper() == "YES",
            "default": default or None,
        })
    return [{"name": name, "columns": cols} for name, cols in tables.items()]


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--db", default="sqlite", choices=["sqlite", "postgres"])
    p.add_argument("--connection", default="app.db", help="Connection string or path")
    p.add_argument("--table", default=None, help="Specific table to inspect")


if __name__ == "__main__":
    make_cli(TOOL, "Inspect database schema", run, _add_args)
