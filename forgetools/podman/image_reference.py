"""Validate deterministic Podman image references."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools.podman.common import canonical_image, image_reference


def run(*, image: str) -> ForgeResult:
    """Validate a fully-qualified registry/repository image reference."""
    with Timer() as timer:
        result = image_reference(image)
        if not result["valid"]:
            return ForgeResult.failure(
                "podman.image-reference",
                [str(result.get("error", "invalid image reference"))],
                timer.elapsed_ms,
                f"Use the complete reference, for example `{result.get('suggestion', canonical_image(image))}`",
            )
        return ForgeResult.success("podman.image-reference", result, timer.elapsed_ms)


def _args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--image", required=True, help="Full image reference, e.g. docker.io/library/nginx:1.27 or ghcr.io/org/app:1.0")


if __name__ == "__main__":
    make_cli("podman.image-reference", "Validate a deterministic fully-qualified Podman image reference", run, _args)
