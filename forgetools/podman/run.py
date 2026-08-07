"""Create and start Podman containers with bastion-safe port allocation."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command
from forgetools.podman.common import image_reference, target, validate_publications


def run(
    *,
    image: str,
    ports: list[str] | None = None,
    name: str = "",
    command: list[str] | None = None,
    detach: bool = True,
    allow_local_image: bool = False,
    execute: bool = False,
    confirm: bool = False,
    connection: str = "",
    url: str = "",
    remote: bool = False,
    cwd: str | None = None,
) -> ForgeResult:
    """Preview or execute a container start while enforcing bastion ports."""
    with Timer() as timer:
        ports = ports or []
        command = command or []
        reference = image_reference(image)
        is_local = image.startswith("localhost/") or ("/" not in image and not image.startswith(("docker.io/", "ghcr.io/")))
        if not reference["valid"] and not (allow_local_image and is_local):
            return ForgeResult.failure("podman.run", [str(reference.get("error", "image must be fully qualified"))], timer.elapsed_ms, "Use docker.io/library/image:tag, ghcr.io/org/image:tag, or set allow_local_image=true for an image already stored locally")
        parsed, violations = validate_publications(ports)
        if violations:
            return ForgeResult.failure("podman.run", violations, timer.elapsed_ms, "Select the first free host port with podman.select-port and use only 30000-30399")
        podman_target = target(connection, url, remote)
        if error := podman_target.validate():
            return ForgeResult.failure("podman.run", [error], timer.elapsed_ms)
        cmd = podman_target.prefix() + ["run"]
        if detach:
            cmd.append("--detach")
        if name:
            cmd.extend(["--name", name])
        for value in ports:
            cmd.extend(["--publish", value])
        cmd.append(image)
        cmd.extend(command)
        plan = {"command": cmd, "image": image, "ports": parsed, "connection": connection or None, "url": url or None, "remote": bool(remote or connection or url)}
        if not execute:
            return ForgeResult.success("podman.run", {**plan, "preview": True, "executed": False, "requires_confirmation": True}, timer.elapsed_ms)
        if not confirm:
            return ForgeResult.failure("podman.run", ["Explicit confirmation is required before starting a container"], timer.elapsed_ms, "Review the preview, then call again with execute=true and confirm=true")
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=300)
        except FileNotFoundError:
            return ForgeResult.failure("podman.run", ["podman not found"], timer.elapsed_ms, "Install Podman and verify the target connection")
        except Exception as exc:
            return ForgeResult.failure("podman.run", [str(exc)], timer.elapsed_ms)
        if rc != 0:
            return ForgeResult.failure("podman.run", [stderr.strip() or stdout.strip() or "podman run failed"], timer.elapsed_ms, "Inspect the image, ports, rootless permissions, and remote connection")
        return ForgeResult.success("podman.run", {**plan, "stdout": stdout, "stderr": stderr, "preview": False, "executed": True}, timer.elapsed_ms)


def _args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--image", required=True, help="Full registry image or local image with --allow-local-image")
    parser.add_argument("--port", dest="ports", action="append", default=[], help="Host:container[/protocol]; repeat for multiple ports")
    parser.add_argument("--name", default="")
    parser.add_argument("--command", nargs="*", default=[])
    parser.add_argument("--no-detach", dest="detach", action="store_false", default=True)
    parser.add_argument("--allow-local-image", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--connection", default="", help="Named Podman system connection")
    parser.add_argument("--url", default="", help="Podman service URL (ssh://, unix://, or tcp://)")
    parser.add_argument("--remote", action="store_true", help="Use the remote Podman client")


if __name__ == "__main__":
    make_cli("podman.run", "Preview or execute a bastion-safe Podman container start", run, _args)
