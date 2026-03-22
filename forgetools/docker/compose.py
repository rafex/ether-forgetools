"""forgetools.docker.compose — Docker Compose operations."""
from __future__ import annotations

import argparse
import json

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "docker.compose"

_SUGGESTION = "Ensure docker-compose.yml exists in cwd"
_VALID_ACTIONS = ("up", "down", "ps", "logs", "restart", "stop")


def _compose_base(cwd: str | None) -> list[str] | None:
    """Return ['docker', 'compose'] or ['docker-compose'], or None if neither found."""
    import shutil
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def run(
    *,
    action: str,
    service: str | None = None,
    cwd: str | None = None,
    detach: bool = True,
    tail: int = 100,
) -> ForgeResult:
    with Timer() as t:
        if action not in _VALID_ACTIONS:
            return ForgeResult.failure(
                TOOL,
                [f"Invalid action: {action}. Choose from: {', '.join(_VALID_ACTIONS)}"],
                duration_ms=t.elapsed_ms,
            )

        base = _compose_base(cwd)
        if base is None:
            return ForgeResult.failure(
                TOOL, ["docker or docker-compose not found"],
                duration_ms=t.elapsed_ms, suggestion=_SUGGESTION
            )

        cmd = base[:]
        if action == "up":
            cmd.append("up")
            if detach:
                cmd.append("-d")
            if service:
                cmd.append(service)
        elif action == "down":
            cmd.append("down")
            if service:
                cmd.append(service)
        elif action == "ps":
            cmd.extend(["ps", "--format", "json"])
        elif action == "logs":
            cmd.extend(["logs", f"--tail={tail}"])
            if service:
                cmd.append(service)
        elif action in ("restart", "stop"):
            cmd.append(action)
            if service:
                cmd.append(service)

        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd)
        except FileNotFoundError:
            return ForgeResult.failure(
                TOOL, ["docker not found"],
                duration_ms=t.elapsed_ms, suggestion=_SUGGESTION
            )
        if rc != 0:
            return ForgeResult.failure(
                TOOL, [stderr.strip() or f"docker compose {action} failed"],
                duration_ms=t.elapsed_ms, suggestion=_SUGGESTION
            )

        data = _parse(action, stdout, service, tail)
        return ForgeResult.success(TOOL, data, t.elapsed_ms)


def _parse(action: str, stdout: str, service: str | None, tail: int) -> dict:
    if action == "ps":
        services = []
        for line in stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                ports = obj.get("Publishers") or []
                port_strs = [
                    f"{p.get('PublishedPort', '')}:{p.get('TargetPort', '')}/{p.get('Protocol', '')}"
                    for p in ports if p.get("PublishedPort")
                ]
                services.append({
                    "name": obj.get("Name", obj.get("Service", "")),
                    "image": obj.get("Image", ""),
                    "status": obj.get("Status", obj.get("State", "")),
                    "ports": port_strs,
                })
            except (json.JSONDecodeError, AttributeError):
                continue
        return {"services": services}
    elif action == "logs":
        lines = stdout.splitlines()
        return {"service": service, "lines": lines, "count": len(lines)}
    else:
        return {"action": action, "service": service, "output": stdout.strip()[:1024]}


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", required=True, choices=list(_VALID_ACTIONS))
    p.add_argument("--service", default=None, help="Service name")
    p.add_argument("--no-detach", dest="detach", action="store_false", default=True)
    p.add_argument("--tail", type=int, default=100)


if __name__ == "__main__":
    make_cli(TOOL, "Docker Compose operations", run, _add_args)
