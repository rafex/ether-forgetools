from __future__ import annotations

from pathlib import Path

from forgetools.podman.common import image_reference, target, validate_publications
from forgetools.podman.build import run as build_run
from forgetools.podman.connection import run as connection_run
from forgetools.podman.run import run as container_run


def test_image_references_require_registry_path_and_tag() -> None:
    assert image_reference("docker.io/library/nginx:1.27")["valid"] is True
    assert image_reference("ghcr.io/owner/api@sha256:abc")["valid"] is True
    assert image_reference("nginx")["valid"] is False
    assert image_reference("docker.io/nginx")["valid"] is False


def test_publications_enforce_bastion_ranges() -> None:
    parsed, errors = validate_publications(["30180:8080", "80:80", "RANDOM"])
    assert parsed[0]["category"] == "api"
    assert any("80" in error for error in errors)
    assert any("RANDOM" in error for error in errors)


def test_remote_target_is_explicit_and_mutually_exclusive() -> None:
    assert target(connection="bastion").prefix() == ["podman", "--remote", "--connection", "bastion"]
    assert target(url="ssh://user@bastion/run/user/1000/podman/podman.sock").prefix() == [
        "podman", "--remote", "--url", "ssh://user@bastion/run/user/1000/podman/podman.sock"
    ]
    assert target(connection="bastion", url="ssh://user@bastion/socket").validate()


def test_connection_mutations_default_to_preview() -> None:
    result = connection_run(
        action="add",
        name="bastion",
        destination="ssh://user@bastion/run/user/1000/podman/podman.sock",
    )
    assert result.ok
    assert result.data["preview"] is True
    assert result.data["executed"] is False
    assert result.data["requires_confirmation"] is True


def test_run_preview_rejects_forbidden_ports_without_invoking_podman() -> None:
    result = container_run(
        image="docker.io/library/nginx:1.27",
        ports=["80:80"],
    )
    assert result.ok is False
    assert "outside the approved bastion ranges" in result.errors[0]


def test_run_preview_contains_remote_command() -> None:
    result = container_run(
        image="ghcr.io/owner/api:1.0",
        ports=["30180:8080"],
        connection="bastion",
    )
    assert result.ok
    assert result.data["preview"] is True
    assert result.data["command"][:4] == ["podman", "--remote", "--connection", "bastion"]
    assert "30180:8080" in result.data["command"]


def test_build_rejects_unqualified_external_base_image(tmp_path: Path) -> None:
    containerfile = tmp_path / "Containerfile"
    containerfile.write_text("FROM nginx:latest\n")
    result = build_run(tag="localhost/test:latest", containerfile=str(containerfile), cwd="/")
    assert result.ok is False
    assert "fully qualified" in result.errors[0]
