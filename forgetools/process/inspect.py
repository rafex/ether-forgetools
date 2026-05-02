from __future__ import annotations

"""
process/inspect.py — Deep inspection of a running process by PID.

Actions:
    info        — full details: pid, ppid, pgid, user, cpu%, mem%, rss, vsz,
                  state, start time, elapsed, command, working directory
    env         — environment variables of the process
    files       — open file descriptors (lsof -p <pid>)
    connections — open network connections of the process (lsof -p <pid> -i)
    tree        — parent chain from PID up to init, and direct children
    threads     — thread count and thread list (Linux: /proc; macOS: ps -M)
"""

import argparse
import os
import platform
import re
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "process.inspect"
_IS_MAC   = platform.system() == "Darwin"
_IS_LINUX = platform.system() == "Linux"


# ── helpers ───────────────────────────────────────────────────────────────────

def _ps_pid(pid: int, fmt: str) -> tuple[int, str, str]:
    if _IS_MAC:
        return run_command(["ps", "-p", str(pid), "-o", fmt], timeout=5)
    return run_command(["ps", "-p", str(pid), "-o", fmt, "--no-headers"], timeout=5)


def _parse_ps_line(line: str, fields: list[str]) -> dict:
    """Split a ps output line into a dict by fixed field count."""
    parts = line.split(None, len(fields) - 1)
    return {k: (parts[i].strip() if i < len(parts) else "") for i, k in enumerate(fields)}


def _lsof(pid: int, extra_args: list[str] | None = None) -> list[dict]:
    cmd = ["lsof", "-p", str(pid), "-F", "0"]
    if extra_args:
        cmd += extra_args
    rc, stdout, stderr = run_command(cmd, timeout=10)
    if rc != 0:
        return []
    # lsof -F0 uses NUL bytes as field terminators; on macOS multiple fields
    # may appear on one line separated by NUL bytes.  Normalise by splitting
    # on both NUL (\x00) and newlines so each token is one field.
    entries: list[dict] = []
    current: dict = {}
    tokens = [t for t in stdout.replace("\n", "\x00").split("\x00") if t]
    for token in tokens:
        indicator = token[0]
        value     = token[1:].strip()
        if indicator == "p":       # new process block
            if current:
                entries.append(current)
            current = {"pid": value}
        elif indicator == "f":     # new file descriptor block
            if "fd" in current or "type" in current:
                entries.append(current)
                current = {"pid": current.get("pid", "")}
            current["fd"] = value
        elif indicator == "t":
            current["type"] = value
        elif indicator == "n":
            current["name"] = value
        elif indicator == "P":
            current["protocol"] = value
        elif indicator == "s":
            current["state"] = value
        elif indicator == "T":
            # TCP flags: ST=state
            if value.startswith("ST="):
                current["tcp_state"] = value[3:]
        elif indicator == "c":
            current["command"] = value
        elif indicator == "u":
            current["uid"] = value
    if current:
        entries.append(current)
    return entries


def _proc_cwd(pid: int) -> str | None:
    if _IS_LINUX:
        try:
            return str(Path(f"/proc/{pid}/cwd").resolve())
        except Exception:
            return None
    if _IS_MAC:
        rc, out, _ = run_command(["lsof", "-p", str(pid), "-Fn"], timeout=5)
        if rc == 0:
            for line in out.splitlines():
                if line.startswith("n") and "/" in line[1:]:
                    return line[1:]
    return None


def _proc_env(pid: int) -> dict[str, str]:
    """Read process environment variables."""
    if _IS_LINUX:
        try:
            raw = Path(f"/proc/{pid}/environ").read_bytes()
            pairs = raw.split(b"\x00")
            result = {}
            for p in pairs:
                if b"=" in p:
                    k, _, v = p.partition(b"=")
                    result[k.decode(errors="replace")] = v.decode(errors="replace")
            return result
        except PermissionError:
            return {"error": "Permission denied — try sudo"}
        except FileNotFoundError:
            return {"error": f"Process {pid} not found"}
    if _IS_MAC:
        # macOS: `ps eww -p PID` embeds env in the command line
        rc, out, _ = run_command(["ps", "eww", "-p", str(pid)], timeout=5)
        if rc != 0:
            return {"error": "ps eww failed"}
        lines = [l for l in out.splitlines() if l.strip() and not l.strip().startswith("PID")]
        env: dict[str, str] = {}
        for line in lines:
            # env vars are appended after the command, space separated, KEY=VALUE
            for token in re.findall(r'(\w+=\S*)', line):
                k, _, v = token.partition("=")
                if k and v:
                    env[k] = v
        return env
    return {"error": f"Unsupported platform: {platform.system()}"}


# ── actions ───────────────────────────────────────────────────────────────────

def _info(pid: int) -> dict:
    if _IS_MAC:
        fields_fmt = "pid,ppid,pgid,uid,user,%cpu,%mem,rss,vsz,stat,lstart,time,command"
    else:
        fields_fmt = "pid,ppid,pgid,uid,user,%cpu,%mem,rss,vsz,stat,lstart,time,command"

    rc, stdout, stderr = run_command(
        ["ps", "-p", str(pid), "-o", fields_fmt],
        timeout=5,
    )
    if rc != 0:
        raise RuntimeError(f"Process {pid} not found")

    lines = [l for l in stdout.splitlines() if l.strip() and not l.lstrip().startswith("PID")]
    if not lines:
        raise RuntimeError(f"Process {pid} not found")

    # Parse the line; command is last and may have spaces
    raw = lines[0].split()
    def _take(n): return raw.pop(0) if raw else ""
    info: dict = {
        "pid":     int(_take(1) or pid),
        "ppid":    _take(1),
        "pgid":    _take(1),
        "uid":     _take(1),
        "user":    _take(1),
        "cpu_pct": _take(1),
        "mem_pct": _take(1),
        "rss_kb":  _take(1),
        "vsz_kb":  _take(1),
        "state":   _take(1),
    }
    # Remaining tokens: lstart (multiple words) + time + command
    remaining = lines[0].split(None, 10)
    if len(remaining) > 10:
        info["command"] = remaining[-1].strip()

    # Working directory
    cwd = _proc_cwd(pid)
    if cwd:
        info["cwd"] = cwd

    return info


def _env_action(pid: int, filter_key: str | None) -> dict:
    env = _proc_env(pid)
    if filter_key:
        env = {k: v for k, v in env.items() if filter_key.lower() in k.lower()}
    return {"pid": pid, "count": len(env), "env": env}


def _files(pid: int) -> dict:
    entries = _lsof(pid)
    # Remove network entries (those are for connections action)
    file_entries = [e for e in entries if e.get("type") not in ("IPv4", "IPv6", "unix") and "fd" in e]
    return {
        "pid":   pid,
        "count": len(file_entries),
        "files": file_entries,
    }


def _connections(pid: int) -> dict:
    entries = _lsof(pid, ["-i"])
    net_entries = [e for e in entries if e.get("type") in ("IPv4", "IPv6") or e.get("protocol")]
    # Also include unix sockets
    unix_entries = _lsof(pid)
    unix_entries = [e for e in unix_entries if e.get("type") == "unix"]

    return {
        "pid":         pid,
        "net_count":   len(net_entries),
        "unix_count":  len(unix_entries),
        "connections": net_entries,
        "unix_sockets": unix_entries,
    }


def _tree(pid: int) -> dict:
    # Build parent chain up to PID 1
    chain = []
    current = pid
    visited = set()
    while current and current not in visited:
        visited.add(current)
        rc, out, _ = run_command(
            ["ps", "-p", str(current), "-o", "pid,ppid,user,command"],
            timeout=5,
        )
        if rc != 0:
            break
        lines = [l for l in out.splitlines() if l.strip() and not l.strip().startswith("PID")]
        if not lines:
            break
        parts = lines[0].split(None, 3)
        chain.append({
            "pid":     int(parts[0]) if parts else current,
            "ppid":    int(parts[1]) if len(parts) > 1 else 0,
            "user":    parts[2] if len(parts) > 2 else "",
            "command": parts[3].strip() if len(parts) > 3 else "",
        })
        parent = int(parts[1]) if len(parts) > 1 else 0
        if parent <= 1:
            break
        current = parent

    # Find direct children
    rc2, out2, _ = run_command(
        ["ps", "-A", "-o", "pid,ppid,user,command"],
        timeout=5,
    )
    children = []
    if rc2 == 0:
        for line in out2.splitlines():
            parts = line.split(None, 3)
            if len(parts) >= 2 and parts[1].strip() == str(pid):
                try:
                    children.append({
                        "pid":     int(parts[0]),
                        "user":    parts[2] if len(parts) > 2 else "",
                        "command": parts[3].strip() if len(parts) > 3 else "",
                    })
                except ValueError:
                    pass

    return {
        "pid":          pid,
        "parent_chain": chain,
        "children":     children,
        "depth":        len(chain),
    }


def _threads(pid: int) -> dict:
    if _IS_LINUX:
        try:
            task_dir = Path(f"/proc/{pid}/task")
            tids = [int(t.name) for t in task_dir.iterdir() if t.is_dir()]
            return {"pid": pid, "thread_count": len(tids), "tids": tids}
        except Exception as e:
            return {"pid": pid, "error": str(e)}
    if _IS_MAC:
        rc, out, _ = run_command(["ps", "-M", "-p", str(pid)], timeout=5)
        if rc != 0:
            return {"pid": pid, "error": "ps -M failed"}
        lines = [l for l in out.splitlines() if l.strip() and not l.strip().startswith("PID")]
        return {"pid": pid, "thread_count": len(lines), "threads_raw": lines}
    return {"pid": pid, "error": f"Unsupported: {platform.system()}"}


# ── public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action:     str = "info",
    pid:        int | None = None,
    filter_key: str | None = None,   # for env: grep by key name
    cwd:        str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if pid is None:
            return ForgeResult.failure(TOOL, ["--pid is required"], t.elapsed_ms)

        try:
            if action == "info":
                data = _info(pid)
            elif action == "env":
                data = _env_action(pid, filter_key)
            elif action == "files":
                data = _files(pid)
            elif action == "connections":
                data = _connections(pid)
            elif action == "tree":
                data = _tree(pid)
            elif action == "threads":
                data = _threads(pid)
            else:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unknown action '{action}'. Use: info | env | files | connections | tree | threads"],
                    t.elapsed_ms,
                )
        except RuntimeError as exc:
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="info",
                   choices=["info", "env", "files", "connections", "tree", "threads"])
    p.add_argument("--pid",        type=int, default=None, help="Process ID (required)")
    p.add_argument("--filter-key", default=None, dest="filter_key",
                   help="Filter env vars by key substring (action=env)")


if __name__ == "__main__":
    make_cli(TOOL, "Deep process inspection: info, env, files, connections, tree, threads", run, _add_args)
