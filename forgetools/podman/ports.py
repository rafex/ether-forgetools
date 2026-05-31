"""forgetools.podman.ports - Inspect occupied Podman published ports."""
from __future__ import annotations

import re

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

RANGES = {
    "web": range(30000, 30100),
    "api": range(30100, 30200),
    "database": range(30200, 30300),
    "temporal": range(30300, 30400),
}

PORT_RE = re.compile(r"(?:(?:0\.0\.0\.0|127\.0\.0\.1|::):)?(\d+)->")


def _used_ports(cwd: str | None = None) -> tuple[list[int], str]:
    rc, stdout, stderr = run_command(["podman", "ps", "--format", "{{.Ports}}"], cwd=cwd, timeout=20)
    if rc != 0:
        raise RuntimeError(stderr.strip() or "podman ps failed")
    ports = sorted({int(match) for match in PORT_RE.findall(stdout)})
    return ports, stdout


def run(*, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            used, raw = _used_ports(cwd)
        except Exception as exc:
            return ForgeResult.failure("podman.ports", [str(exc)], t.elapsed_ms, "Install podman and ensure the Podman API/context is available.")
        available = {
            name: [port for port in ports if port not in used][:10]
            for name, ports in RANGES.items()
        }
        return ForgeResult.success("podman.ports", {"used": used, "available_preview": available, "raw": raw}, t.elapsed_ms)


if __name__ == "__main__":
    make_cli("podman.ports", "Inspect occupied Podman published ports", run)
