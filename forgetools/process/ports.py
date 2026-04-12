from __future__ import annotations

"""
process/ports.py — Network port inspection and process-by-port lookup.

Actions:
    by-port     — find process(es) listening on a given port (like the example:
                  ps -p $(lsof -ti:<port>) -o pid,ppid,command)
    all         — all listening TCP/UDP ports with owning process info
    by-pid      — all ports opened by a given PID
    listen      — summary of all listening sockets (TCP + UDP)
    established — established TCP connections with process info
"""

import argparse
import platform
import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "process.ports"
_IS_MAC   = platform.system() == "Darwin"
_IS_LINUX = platform.system() == "Linux"


# ── helpers ───────────────────────────────────────────────────────────────────

def _lsof_network(extra: list[str] | None = None) -> list[dict]:
    """Run lsof for network connections and return parsed entries."""
    cmd = ["lsof", "-n", "-P", "-F", "0", "-i"]
    if extra:
        cmd += extra
    rc, stdout, _ = run_command(cmd, timeout=10)
    if rc != 0:
        return []

    # lsof -F 0 uses NUL bytes as field terminators; on macOS multiple fields
    # can appear on one line separated by NUL bytes.  Normalise by splitting
    # on both NUL (\x00) and newlines so each token is one "field code + value".
    tokens = [t for t in stdout.replace("\n", "\x00").split("\x00") if t]

    entries: list[dict] = []
    current: dict = {}
    pid_meta: dict[str, dict] = {}   # pid → {command, user}

    for token in tokens:
        indicator = token[0]
        value     = token[1:].strip()

        if indicator == "p":
            if "fd" in current or "name" in current:
                entries.append(current)
            current = {"pid": value}
            # Carry forward metadata for this pid if we already have it
            if value in pid_meta:
                current.update(pid_meta[value])
        elif indicator == "c":
            current["command"] = value
            pid_meta.setdefault(current.get("pid", ""), {})["command"] = value
        elif indicator == "u":
            current["uid"] = value
        elif indicator == "f":
            if "name" in current or "protocol" in current:
                entries.append(current)
                new = {"pid": current.get("pid", ""),
                       "command": current.get("command", ""),
                       "uid": current.get("uid", "")}
                current = new
            current["fd"] = value
        elif indicator == "t":
            current["type"] = value
        elif indicator == "P":
            current["protocol"] = value
        elif indicator == "n":
            current["name"] = value
        elif indicator == "s":
            current["state"] = value
        elif indicator == "T":
            if value.startswith("ST="):
                current["tcp_state"] = value[3:]

    if current and ("name" in current or "protocol" in current):
        entries.append(current)

    return entries


def _ps_info(pid: str) -> dict:
    """Get process info for a single PID."""
    rc, out, _ = run_command(
        ["ps", "-p", pid, "-o", "pid,ppid,pgid,user,%cpu,%mem,command"],
        timeout=5,
    )
    if rc != 0:
        return {"pid": pid, "error": "not found"}
    lines = [l for l in out.splitlines() if l.strip() and not l.lstrip().startswith("PID")]
    if not lines:
        return {"pid": pid, "error": "not found"}
    parts = lines[0].split(None, 6)
    return {
        "pid":     parts[0] if len(parts) > 0 else pid,
        "ppid":    parts[1] if len(parts) > 1 else "",
        "pgid":    parts[2] if len(parts) > 2 else "",
        "user":    parts[3] if len(parts) > 3 else "",
        "cpu_pct": parts[4] if len(parts) > 4 else "",
        "mem_pct": parts[5] if len(parts) > 5 else "",
        "command": parts[6].strip() if len(parts) > 6 else "",
    }


def _parse_address(name: str) -> tuple[str, str]:
    """Extract host and port from an lsof address like '*:8080' or '127.0.0.1:8080'."""
    if name.startswith("["):
        # IPv6: [::1]:8080 or [::]:*
        m = re.match(r'\[([^\]]+)\]:(.+)', name)
        if m:
            return m.group(1), m.group(2)
        return name, ""
    parts = name.rsplit(":", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return name, ""


def _port_number(name: str) -> str | None:
    """Extract numeric or named port from an lsof 'name' field like '*:8080' or '->host:port'."""
    # For LISTEN/BOUND entries the name is like *:8080 or 0.0.0.0:8080
    _, port = _parse_address(name)
    if port and port != "*":
        return port
    return None


# ── actions ───────────────────────────────────────────────────────────────────

def _by_port(port: int) -> dict:
    """Replicate: ps -p $(lsof -ti:<port>) -o pid,ppid,command — plus more detail."""
    # Get PIDs for this port
    rc, pids_str, _ = run_command(["lsof", "-ti", f":{port}"], timeout=8)
    pids = [p.strip() for p in pids_str.splitlines() if p.strip()] if rc == 0 else []

    if not pids:
        # Try with lsof -i TCP:<port> for more thorough lookup
        rc2, out2, _ = run_command(
            ["lsof", "-n", "-P", "-i", f"TCP:{port}", "-i", f"UDP:{port}"],
            timeout=8,
        )
        if rc2 == 0:
            for line in out2.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    if parts[1] not in pids:
                        pids.append(parts[1])

    processes = [_ps_info(pid) for pid in pids]

    # Also get connection entries for context
    entries = _lsof_network([f"TCP:{port}", f"-i", f"UDP:{port}"])
    connections = [e for e in entries if str(port) in e.get("name", "")]

    return {
        "port":        port,
        "pid_count":   len(pids),
        "pids":        pids,
        "processes":   processes,
        "connections": connections,
    }


def _all_ports() -> dict:
    """All network sockets (listen + established) with process info."""
    entries = _lsof_network()
    # De-duplicate by (pid, name) and enrich
    seen = set()
    result = []
    for e in entries:
        key = (e.get("pid", ""), e.get("name", ""), e.get("fd", ""))
        if key in seen:
            continue
        seen.add(key)
        name = e.get("name", "")
        host, port = _parse_address(name)
        row = dict(e)
        row["local_host"] = host
        row["local_port"] = port
        result.append(row)
    return {"count": len(result), "sockets": result}


def _by_pid(pid: int) -> dict:
    """All network sockets opened by a specific PID."""
    entries = _lsof_network([f"-a", "-p", str(pid)])
    seen = set()
    result = []
    for e in entries:
        if e.get("pid") != str(pid):
            continue
        key = (e.get("name", ""), e.get("fd", ""), e.get("tcp_state", ""))
        if key in seen:
            continue
        seen.add(key)
        name = e.get("name", "")
        host, port = _parse_address(name)
        row = dict(e)
        row["local_host"] = host
        row["local_port"] = port
        result.append(row)
    return {"pid": pid, "count": len(result), "sockets": result}


def _listen() -> dict:
    """Listening TCP/UDP ports with owning process — compact summary."""
    if _IS_LINUX:
        cmd = ["ss", "-tlnup"]
        rc, out, _ = run_command(cmd, timeout=8)
        if rc == 0:
            rows = []
            for line in out.splitlines():
                if "LISTEN" not in line and "udp" not in line.lower():
                    continue
                parts = line.split()
                if len(parts) < 5:
                    continue
                rows.append({"proto": parts[0], "local": parts[4] if len(parts) > 4 else "",
                              "process": parts[-1] if parts[-1].startswith("users:") else ""})
            return {"count": len(rows), "listening": rows}

    # macOS / fallback
    entries = _lsof_network()
    listening = []
    for e in entries:
        state = e.get("tcp_state") or e.get("state") or ""
        name  = e.get("name", "")
        proto = e.get("protocol") or e.get("type") or ""
        # LISTEN entries: tcp_state=LISTEN or UDP entries with *:port
        if "LISTEN" in state.upper() or (proto in ("UDP", "udp") and "*:" in name):
            host, port = _parse_address(name)
            listening.append({
                "pid":     e.get("pid", ""),
                "command": e.get("command", ""),
                "proto":   proto,
                "port":    port,
                "host":    host,
                "state":   state,
            })
    # De-dup
    seen = set()
    deduped = []
    for l in listening:
        k = (l["pid"], l["port"], l["proto"])
        if k not in seen:
            seen.add(k)
            deduped.append(l)
    deduped.sort(key=lambda x: x.get("port", ""))
    return {"count": len(deduped), "listening": deduped}


def _established() -> dict:
    """Established TCP connections with process info."""
    entries = _lsof_network()
    estab = []
    for e in entries:
        state = e.get("tcp_state") or e.get("state") or ""
        if "ESTABLISHED" in state.upper():
            name = e.get("name", "")
            # Established: local->remote
            parts = name.split("->")
            local = parts[0] if parts else name
            remote = parts[1] if len(parts) > 1 else ""
            lh, lp = _parse_address(local)
            rh, rp = _parse_address(remote)
            estab.append({
                "pid":          e.get("pid", ""),
                "command":      e.get("command", ""),
                "protocol":     e.get("protocol") or e.get("type") or "",
                "local_host":   lh,
                "local_port":   lp,
                "remote_host":  rh,
                "remote_port":  rp,
                "state":        state,
            })
    estab.sort(key=lambda x: x.get("local_port", ""))
    return {"count": len(estab), "connections": estab}


# ── public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action: str = "listen",
    port:   int | None = None,
    pid:    int | None = None,
    cwd:    str | None = None,
) -> ForgeResult:
    with Timer() as t:
        try:
            if action == "by-port":
                if port is None:
                    return ForgeResult.failure(TOOL, ["--port is required for action=by-port"], t.elapsed_ms)
                data = _by_port(port)
            elif action == "all":
                data = _all_ports()
            elif action == "by-pid":
                if pid is None:
                    return ForgeResult.failure(TOOL, ["--pid is required for action=by-pid"], t.elapsed_ms)
                data = _by_pid(pid)
            elif action == "listen":
                data = _listen()
            elif action == "established":
                data = _established()
            else:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unknown action '{action}'. Use: by-port | all | by-pid | listen | established"],
                    t.elapsed_ms,
                )
        except Exception as exc:
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="listen",
                   choices=["by-port", "all", "by-pid", "listen", "established"])
    p.add_argument("--port", type=int, default=None, help="Port number (for action=by-port)")
    p.add_argument("--pid",  type=int, default=None, help="Process ID (for action=by-pid)")


if __name__ == "__main__":
    make_cli(TOOL, "Network port inspection: find process by port, list listening ports, etc.", run, _add_args)
