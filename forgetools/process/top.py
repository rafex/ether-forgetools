from __future__ import annotations

"""
process/top.py — Rank running processes by resource usage.

Actions:
    cpu         — top N processes by CPU usage
    memory      — top N processes by memory (RSS) usage
    zombie      — list zombie / defunct processes
    threads     — processes with most threads
    io          — processes with highest I/O (Linux: /proc/PID/io; macOS: iotop unavailable — uses ps)
    open-files  — processes with most open file descriptors (lsof)
    summary     — one-shot overview: top-3 cpu, top-3 mem, zombie count, thread leaders
"""

import argparse
import platform
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "process.top"
_IS_MAC   = platform.system() == "Darwin"
_IS_LINUX = platform.system() == "Linux"

_DEFAULT_N = 10


# ── helpers ───────────────────────────────────────────────────────────────────

def _ps_all(extra_fields: str = "") -> list[dict]:
    """
    Run `ps aux` (or extended) and return a list of dicts.
    Always returns: pid, ppid, user, cpu_pct, mem_pct, rss_kb, vsz_kb, stat, command
    """
    fmt = "pid,ppid,user,%cpu,%mem,rss,vsz,stat,command"
    if extra_fields:
        fmt = fmt.rstrip(",command") + f",{extra_fields},command"

    if _IS_MAC:
        rc, out, _ = run_command(["ps", "-A", "-o", fmt], timeout=10)
    else:
        rc, out, _ = run_command(["ps", "-A", "-o", fmt, "--no-headers"], timeout=10)

    if rc != 0:
        return []

    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.lstrip().startswith("PID"):
            continue
        parts = line.split(None, 8)
        if len(parts) < 8:
            continue
        try:
            rows.append({
                "pid":     parts[0],
                "ppid":    parts[1],
                "user":    parts[2],
                "cpu_pct": float(parts[3]),
                "mem_pct": float(parts[4]),
                "rss_kb":  int(parts[5]),
                "vsz_kb":  int(parts[6]),
                "stat":    parts[7],
                "command": parts[8].strip() if len(parts) > 8 else "",
            })
        except (ValueError, IndexError):
            continue
    return rows


def _thread_count_linux(pid: str) -> int:
    try:
        task_dir = Path(f"/proc/{pid}/task")
        return sum(1 for t in task_dir.iterdir() if t.is_dir())
    except Exception:
        return 0


def _thread_count_mac_from_stat(stat: str) -> int:
    """ps stat field on macOS encodes thread count after the state letter for some processes."""
    return 0  # ps -M is needed for accurate count; not available from stat field


# ── actions ───────────────────────────────────────────────────────────────────

def _top_cpu(n: int) -> dict:
    rows = _ps_all()
    rows.sort(key=lambda r: r["cpu_pct"], reverse=True)
    top = rows[:n]
    return {
        "metric":    "cpu_pct",
        "top_count": len(top),
        "processes": top,
    }


def _top_memory(n: int) -> dict:
    rows = _ps_all()
    rows.sort(key=lambda r: r["rss_kb"], reverse=True)
    top = rows[:n]
    total_rss = sum(r["rss_kb"] for r in rows)
    return {
        "metric":        "rss_kb",
        "total_rss_kb":  total_rss,
        "top_count":     len(top),
        "processes":     top,
    }


def _zombies() -> dict:
    rows = _ps_all()
    zombies = [r for r in rows if r["stat"].startswith("Z") or "defunct" in r["command"].lower()]
    return {
        "zombie_count": len(zombies),
        "zombies":      zombies,
    }


def _top_threads(n: int) -> dict:
    rows = _ps_all()
    enriched = []
    for r in rows:
        if _IS_LINUX:
            tc = _thread_count_linux(r["pid"])
        else:
            # macOS: use nlwp field if ps supports it, otherwise leave at 1
            rc, out, _ = run_command(
                ["ps", "-p", r["pid"], "-o", "nlwp="],
                timeout=3,
            )
            try:
                tc = int(out.strip()) if rc == 0 and out.strip().isdigit() else 1
            except ValueError:
                tc = 1
        r["thread_count"] = tc
        enriched.append(r)

    enriched.sort(key=lambda r: r["thread_count"], reverse=True)
    top = enriched[:n]
    return {
        "metric":    "thread_count",
        "top_count": len(top),
        "processes": top,
    }


def _top_io(n: int) -> dict:
    """Linux: read /proc/PID/io; macOS: approximate via ps (no iotop without sudo)."""
    if _IS_LINUX:
        proc = Path("/proc")
        results = []
        for pid_dir in proc.iterdir():
            if not pid_dir.name.isdigit():
                continue
            io_file = pid_dir / "io"
            try:
                text = io_file.read_text()
            except (PermissionError, FileNotFoundError):
                continue
            io_data: dict[str, int] = {}
            for line in text.splitlines():
                k, _, v = line.partition(":")
                try:
                    io_data[k.strip()] = int(v.strip())
                except ValueError:
                    pass
            # Get command
            try:
                cmd = (pid_dir / "comm").read_text().strip()
            except Exception:
                cmd = ""
            read_bytes  = io_data.get("read_bytes", 0)
            write_bytes = io_data.get("write_bytes", 0)
            results.append({
                "pid":         pid_dir.name,
                "command":     cmd,
                "read_bytes":  read_bytes,
                "write_bytes": write_bytes,
                "total_io":    read_bytes + write_bytes,
                "rchar":       io_data.get("rchar", 0),
                "wchar":       io_data.get("wchar", 0),
            })
        results.sort(key=lambda r: r["total_io"], reverse=True)
        return {
            "metric":    "total_io_bytes",
            "note":      "read_bytes/write_bytes = actual disk I/O; rchar/wchar includes cached",
            "top_count": min(n, len(results)),
            "processes": results[:n],
        }
    else:
        # macOS: no easy per-process I/O without DTrace/sudo.  Return note.
        return {
            "metric":    "total_io_bytes",
            "note":      "macOS does not expose per-process I/O without elevated privileges. "
                         "Use: sudo iotop (if installed) or Instruments.app",
            "processes": [],
        }


def _top_open_files(n: int) -> dict:
    """Count open file descriptors per process using lsof."""
    rc, out, _ = run_command(["lsof", "-n", "-P", "-F", "pc"], timeout=15)
    if rc != 0:
        return {"error": "lsof failed", "processes": []}

    counts: dict[str, dict] = {}
    current_pid = ""
    current_cmd = ""
    for line in out.splitlines():
        if not line:
            continue
        indicator = line[0]
        value     = line[1:]
        if indicator == "p":
            current_pid = value
            if current_pid not in counts:
                counts[current_pid] = {"pid": current_pid, "command": "", "fd_count": 0}
        elif indicator == "c":
            current_cmd = value
            if current_pid in counts:
                counts[current_pid]["command"] = value
        elif indicator == "f":
            if current_pid in counts:
                counts[current_pid]["fd_count"] += 1

    ranked = sorted(counts.values(), key=lambda r: r["fd_count"], reverse=True)
    return {
        "metric":    "fd_count",
        "top_count": min(n, len(ranked)),
        "processes": ranked[:n],
    }


def _summary(n: int = 3) -> dict:
    rows = _ps_all()
    rows_cpu = sorted(rows, key=lambda r: r["cpu_pct"], reverse=True)
    rows_mem = sorted(rows, key=lambda r: r["rss_kb"], reverse=True)
    zombies  = [r for r in rows if r["stat"].startswith("Z") or "defunct" in r["command"].lower()]

    total_cpu = sum(r["cpu_pct"] for r in rows)
    total_rss = sum(r["rss_kb"] for r in rows)

    return {
        "process_count": len(rows),
        "total_cpu_pct": round(total_cpu, 1),
        "total_rss_kb":  total_rss,
        "zombie_count":  len(zombies),
        "top_cpu":       rows_cpu[:n],
        "top_memory":    rows_mem[:n],
        "zombies":       zombies,
    }


# ── public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action: str = "cpu",
    n:      int = _DEFAULT_N,
    cwd:    str | None = None,
) -> ForgeResult:
    with Timer() as t:
        try:
            if action == "cpu":
                data = _top_cpu(n)
            elif action == "memory":
                data = _top_memory(n)
            elif action == "zombie":
                data = _zombies()
            elif action == "threads":
                data = _top_threads(n)
            elif action == "io":
                data = _top_io(n)
            elif action == "open-files":
                data = _top_open_files(n)
            elif action == "summary":
                data = _summary(n)
            else:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unknown action '{action}'. Use: cpu | memory | zombie | threads | io | open-files | summary"],
                    t.elapsed_ms,
                )
        except Exception as exc:
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="cpu",
                   choices=["cpu", "memory", "zombie", "threads", "io", "open-files", "summary"])
    p.add_argument("--n", type=int, default=_DEFAULT_N,
                   help=f"Number of top results to return (default {_DEFAULT_N})")


if __name__ == "__main__":
    make_cli(TOOL, "Rank processes by CPU, memory, threads, I/O, open files; list zombies", run, _add_args)
