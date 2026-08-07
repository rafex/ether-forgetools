"""Pull fully-qualified images into a local or remote Podman store."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command
from forgetools.podman.common import image_reference, target


def run(*, image: str, connection: str = "", url: str = "", remote: bool = False, authfile: str = "", cwd: str | None = None) -> ForgeResult:
    """Pull a fully-qualified Docker Hub or GHCR image on the selected service."""
    with Timer() as timer:
        reference = image_reference(image)
        if not reference["valid"]:
            return ForgeResult.failure(
                "podman.pull",
                [str(reference.get("error", "invalid image reference"))],
                timer.elapsed_ms,
                f"Use the complete reference, for example `{reference.get('suggestion', 'docker.io/library/image:latest')}`",
            )
        podman_target = target(connection, url, remote)
        if error := podman_target.validate():
            return ForgeResult.failure("podman.pull", [error], timer.elapsed_ms)
        cmd = podman_target.prefix() + ["pull"]
        if authfile:
            cmd.extend(["--authfile", authfile])
        cmd.append(image)
        try:
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=600)
        except FileNotFoundError:
            return ForgeResult.failure("podman.pull", ["podman not found"], timer.elapsed_ms, "Install Podman and configure the target connection")
        except Exception as exc:
            return ForgeResult.failure("podman.pull", [str(exc)], timer.elapsed_ms)
        if rc != 0:
            return ForgeResult.failure("podman.pull", [stderr.strip() or stdout.strip() or "podman pull failed"], timer.elapsed_ms, "Check registry authentication, the exact tag/digest, and the selected remote connection")
        return ForgeResult.success("podman.pull", {"image": image, "connection": connection or None, "url": url or None, "remote": bool(remote or connection or url), "stdout": stdout, "stderr": stderr}, timer.elapsed_ms)


def _args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--image", required=True, help="Full reference: docker.io/library/image:tag or ghcr.io/org/image:tag")
    parser.add_argument("--authfile", default="", help="Registry authentication file")
    parser.add_argument("--connection", default="", help="Named Podman system connection")
    parser.add_argument("--url", default="", help="Podman service URL (ssh://, unix://, or tcp://)")
    parser.add_argument("--remote", action="store_true", help="Use the remote Podman client")


if __name__ == "__main__":
    make_cli("podman.pull", "Pull a fully-qualified image into a local or remote Podman store", run, _args)
