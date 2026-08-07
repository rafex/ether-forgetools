"""Build images from Containerfiles with an optional remote Podman target."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command
from forgetools.podman.common import image_reference, target


FROM_RE = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(?P<image>\S+)", re.IGNORECASE)


def _base_image_errors(containerfile: str, cwd: str | None, allow_local_base_images: bool) -> list[str]:
    path = Path(cwd or ".") / containerfile
    if not path.is_file():
        return []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        match = FROM_RE.match(line)
        if not match:
            continue
        image = match.group("image")
        if image.lower() == "scratch" or (allow_local_base_images and not image.startswith(("docker.io/", "ghcr.io/"))):
            continue
        reference = image_reference(image)
        if not reference["valid"]:
            errors.append(f"{containerfile}:{line_number}: base image '{image}' is not fully qualified; use '{reference.get('suggestion', 'docker.io/library/image:tag')}'")
    return errors


def run(*, tag: str, containerfile: str = "Containerfile", context: str = ".", no_cache: bool = False, allow_local_base_images: bool = False, connection: str = "", url: str = "", remote: bool = False, cwd: str | None = None) -> ForgeResult:
    """Build an image from a Containerfile on the selected Podman service."""
    with Timer() as timer:
        podman_target = target(connection, url, remote)
        if error := podman_target.validate():
            return ForgeResult.failure("podman.build", [error], timer.elapsed_ms)
        base_image_errors = _base_image_errors(containerfile, cwd, allow_local_base_images)
        if base_image_errors:
            return ForgeResult.failure("podman.build", base_image_errors, timer.elapsed_ms, "Use complete docker.io/... or ghcr.io/... base image references, or set allow_local_base_images=true for a local base image")
        cmd = podman_target.prefix() + ["build", "--file", containerfile, "--tag", tag]
        if no_cache:
            cmd.append("--no-cache")
        cmd.append(context)
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=1800)
        except FileNotFoundError:
            return ForgeResult.failure("podman.build", ["podman not found"], timer.elapsed_ms, "Install Podman and verify the target connection")
        except Exception as exc:
            return ForgeResult.failure("podman.build", [str(exc)], timer.elapsed_ms)
        if rc != 0:
            return ForgeResult.failure("podman.build", [stderr.strip() or stdout.strip() or "podman build failed"], timer.elapsed_ms, "Validate the Containerfile, .containerignore, base image reference, and build context")
        return ForgeResult.success("podman.build", {"tag": tag, "containerfile": containerfile, "context": context, "connection": connection or None, "url": url or None, "remote": bool(remote or connection or url), "stdout": stdout, "stderr": stderr}, timer.elapsed_ms)


def _args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tag", required=True, help="Image tag to create")
    parser.add_argument("--containerfile", default="Containerfile", help="Containerfile or Dockerfile path")
    parser.add_argument("--context", default=".", help="Build context")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--allow-local-base-images", action="store_true", help="Allow local short-name base images already stored on the target")
    parser.add_argument("--connection", default="", help="Named Podman system connection")
    parser.add_argument("--url", default="", help="Podman service URL (ssh://, unix://, or tcp://)")
    parser.add_argument("--remote", action="store_true", help="Use the remote Podman client")


if __name__ == "__main__":
    make_cli("podman.build", "Build an image from a Containerfile on a local or remote Podman service", run, _args)
