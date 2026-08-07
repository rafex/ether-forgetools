"""Shared Podman target, image-reference, and publication-policy helpers."""
from __future__ import annotations

import re
from dataclasses import dataclass

from forgetools.podman.ports import RANGES


_REGISTRY_RE = re.compile(r"^(?P<registry>[^/]+?)(?P<path>/.*)$")
_TAG_RE = re.compile(r"(?::(?P<tag>[^/:@]+))?(?:@(?P<digest>[^/]+))?$")
_PUBLISH_RE = re.compile(
    r"^(?:(?P<ip>[^:]+):)?(?P<host>\d+):(?P<container>\d+)(?:/(?P<protocol>tcp|udp|sctp))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PodmanTarget:
    """Global CLI options used to select a local or remote Podman service."""

    connection: str | None = None
    url: str | None = None
    remote: bool = False

    def validate(self) -> str | None:
        if self.connection and self.url:
            return "connection and url are mutually exclusive"
        if self.connection and any(char.isspace() for char in self.connection):
            return "connection must not contain whitespace"
        if self.url and any(char.isspace() for char in self.url):
            return "url must not contain whitespace"
        if self.url and "://" not in self.url:
            return "url must include a scheme such as ssh://, unix://, or tcp://"
        return None

    def prefix(self) -> list[str]:
        """Return Podman global flags before the subcommand."""
        args = ["podman"]
        if self.remote or self.connection or self.url:
            args.append("--remote")
        if self.connection:
            args.extend(["--connection", self.connection])
        if self.url:
            args.extend(["--url", self.url])
        return args


def target(connection: str | None = None, url: str | None = None, remote: bool = False) -> PodmanTarget:
    return PodmanTarget(connection=connection or None, url=url or None, remote=remote)


def parse_publish(value: str) -> dict[str, str | int] | None:
    """Parse a host:container publication and return its host port."""
    match = _PUBLISH_RE.fullmatch(value.strip())
    if not match:
        return None
    return {
        "raw": value,
        "ip": match.group("ip") or "0.0.0.0",
        "host_port": int(match.group("host")),
        "container_port": int(match.group("container")),
        "protocol": (match.group("protocol") or "tcp").lower(),
    }


def port_category(port: int) -> str | None:
    for category, values in RANGES.items():
        if port in values:
            return category
    return None


def validate_publications(ports: list[str]) -> tuple[list[dict[str, str | int]], list[str]]:
    parsed: list[dict[str, str | int]] = []
    violations: list[str] = []
    for value in ports:
        item = parse_publish(value)
        if item is None:
            violations.append(f"Invalid publication '{value}'; use HOST_PORT:CONTAINER_PORT[/PROTOCOL]")
            continue
        item["category"] = port_category(int(item["host_port"])) or "forbidden"
        parsed.append(item)
        if item["category"] == "forbidden":
            violations.append(
                f"Host port {item['host_port']} is outside the approved bastion ranges"
            )
    return parsed, violations


def image_reference(image: str) -> dict[str, str | bool]:
    """Validate a fully-qualified registry image reference.

    Podman short-name resolution can depend on local aliases and registry
    configuration. Requiring a registry, repository path, and tag/digest makes
    pulls deterministic for docker.io and ghcr.io.
    """
    value = image.strip()
    result: dict[str, str | bool] = {
        "input": image,
        "valid": False,
        "fully_qualified": False,
    }
    if not value or any(char.isspace() for char in value):
        result["error"] = "image must be a non-empty reference without whitespace"
        return result
    if "://" in value:
        result["error"] = "use an image reference, not a transport URL"
        return result

    registry_match = _REGISTRY_RE.match(value)
    if not registry_match:
        result["error"] = "image has no explicit registry"
        result["suggestion"] = canonical_image(value)
        return result

    registry = registry_match.group("registry")
    path_with_suffix = registry_match.group("path").lstrip("/")
    suffix_match = _TAG_RE.search(path_with_suffix)
    if not suffix_match:
        result["error"] = "image reference has no tag or digest"
        result["suggestion"] = f"{value}:latest"
        return result
    repository = path_with_suffix[: suffix_match.start()]
    tag = suffix_match.group("tag") or ""
    digest = suffix_match.group("digest") or ""
    if not repository or "/" not in repository or (not tag and not digest):
        result["error"] = "use registry/repository/image:tag or registry/repository/image@digest"
        result["suggestion"] = canonical_image(value)
        return result

    result.update(
        {
            "valid": True,
            "fully_qualified": True,
            "registry": registry,
            "repository": repository,
            "tag": tag,
            "digest": digest,
        }
    )
    return result


def canonical_image(image: str) -> str:
    """Return the deterministic recommendation for a common short name."""
    value = image.strip()
    if not value:
        return "docker.io/library/image:latest"
    if value.startswith("ghcr.io/") or value.startswith("docker.io/"):
        if ":" not in value.rsplit("/", 1)[-1] and "@" not in value:
            return f"{value}:latest"
        return value
    if "/" not in value:
        return f"docker.io/library/{value if ':' in value else value + ':latest'}"
    return f"docker.io/{value if ':' in value.rsplit('/', 1)[-1] or '@' in value else value + ':latest'}"
