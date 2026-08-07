from __future__ import annotations

"""Remote SpecNative documentation and official installer integration."""

import argparse
import io
import json
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "specnative.upstream"
REPOSITORY = "rafex/SpecNative-Development"
RAW_BASE = f"https://raw.githubusercontent.com/{REPOSITORY}"
RELEASES_URL = f"https://api.github.com/repos/{REPOSITORY}/releases"

DOCUMENT_URLS = {
    "readme": f"{RAW_BASE}/main/README.md",
    "readme-en": f"{RAW_BASE}/main/README.md",
    "readme-es": f"{RAW_BASE}/main/README.es.md",
    "ai-guide": f"{RAW_BASE}/main/docs/ai/index.html",
    "ai-guide-en": f"{RAW_BASE}/main/docs/ai/index.html",
    "ai-guide-es": f"{RAW_BASE}/main/docs/ai/es/index.html",
    "website-es": "https://specnative-d.rafex.io/es/",
    "website-ai-es": "https://specnative-d.rafex.io/ai/es/",
    "architecture": f"{RAW_BASE}/main/Template-Project-Agents-AI/spec-native/ARCHITECTURE.md",
    "mcp": f"{RAW_BASE}/main/Template-Project-Agents-AI/.specnative/MCP.md",
    "schema": f"{RAW_BASE}/main/Template-Project-Agents-AI/.specnative/SCHEMA.md",
    "installer": f"{RAW_BASE}/main/install.py",
}

MAX_RESPONSE_BYTES = 2_000_000
DEFAULT_TIMEOUT_SECONDS = 15


def _fetch(url: str, *, accept: str = "text/plain") -> str:
    return _fetch_bytes(url, accept=accept).decode("utf-8")


def _fetch_bytes(url: str, *, accept: str = "application/octet-stream") -> bytes:
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "forgetools-specnative/0.1",
        },
    )
    with urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError(f"Remote response exceeds {MAX_RESPONSE_BYTES} bytes")
    return payload


def _release_summary(payload: list[dict]) -> list[dict]:
    return [
        {
            "tag_name": release.get("tag_name"),
            "name": release.get("name"),
            "draft": release.get("draft", False),
            "prerelease": release.get("prerelease", False),
            "published_at": release.get("published_at"),
            "html_url": release.get("html_url"),
            "body": release.get("body", ""),
        }
        for release in payload
    ]


def _latest_version() -> str:
    releases = json.loads(_fetch(RELEASES_URL, accept="application/vnd.github+json"))
    if not isinstance(releases, list):
        raise ValueError("GitHub releases response is not a list")
    for release in releases:
        if not release.get("draft") and not release.get("prerelease"):
            tag = release.get("tag_name")
            if tag:
                return str(tag)
    raise ValueError("No stable SpecNative release was found")


def _installer_url(version: str) -> tuple[str, str]:
    resolved = _latest_version() if version in ("", "latest", "main") else version
    if not resolved.startswith("v"):
        resolved = f"v{resolved}"
    return f"{RAW_BASE}/refs/tags/{resolved}/install.py", resolved


def run(
    *,
    action: str = "fetch",
    document: str = "readme-es",
    version: str = "latest",
    target: str = ".",
    profile: str = "team",
    include_examples: bool = False,
    branch: str = "",
    force: bool = False,
    execute: bool = False,
    repo: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    """Fetch current SpecNative sources or preview/execute its official installer.

    Remote reads are intentionally explicit. Installation is preview-only unless
    ``execute=True`` and delegates repository safety checks to upstream install.py.
    """
    with Timer() as timer:
        try:
            if action in {"fetch", "architecture"}:
                key = "architecture" if action == "architecture" else document
                url = DOCUMENT_URLS.get(key)
                if not url:
                    return ForgeResult.failure(
                        TOOL,
                        [f"Unknown document '{document}'"],
                        timer.elapsed_ms,
                        suggestion=f"Use one of: {', '.join(sorted(DOCUMENT_URLS))}",
                    )
                content = _fetch(url)
                return ForgeResult.success(TOOL, {
                    "action": "fetch",
                    "document": key,
                    "url": url,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "content": content,
                }, timer.elapsed_ms)

            if action == "releases":
                payload = json.loads(_fetch(RELEASES_URL, accept="application/vnd.github+json"))
                if not isinstance(payload, list):
                    return ForgeResult.failure(TOOL, ["GitHub releases response is not a list"], timer.elapsed_ms)
                return ForgeResult.success(TOOL, {
                    "repository": REPOSITORY,
                    "url": RELEASES_URL,
                    "releases": _release_summary(payload),
                }, timer.elapsed_ms)

            if action == "install":
                if profile not in {"context", "spec", "team", "platform"}:
                    return ForgeResult.failure(TOOL, [f"Invalid profile '{profile}'"], timer.elapsed_ms)
                target_path = Path(repo or cwd or target).resolve()
                installer_url, resolved_version = _installer_url(version)
                command = [
                    sys.executable,
                    "install.py",
                    "--target", str(target_path),
                    "--version", resolved_version,
                    "--profile", profile,
                ]
                if include_examples:
                    command.append("--include-examples")
                if branch:
                    command.extend(["--branch", branch])
                if force:
                    command.append("--force")

                if not execute:
                    return ForgeResult.success(TOOL, {
                        "action": "install",
                        "executed": False,
                        "repository": REPOSITORY,
                        "version": resolved_version,
                        "installer_url": installer_url,
                        "target": str(target_path),
                        "profile": profile,
                        "command": command,
                        "message": "Preview only. Repeat with execute=true to run the official installer.",
                    }, timer.elapsed_ms)

                archive_url = f"https://codeload.github.com/{REPOSITORY}/tar.gz/refs/tags/{resolved_version}"
                archive = _fetch_bytes(archive_url)
                with tempfile.TemporaryDirectory(prefix="forgetools-specnative-") as temp_dir:
                    source_dir = Path(temp_dir) / "source"
                    source_dir.mkdir()
                    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
                        bundle.extractall(source_dir, filter="data")
                    roots = [path for path in source_dir.iterdir() if path.is_dir()]
                    if len(roots) != 1 or not (roots[0] / "install.py").exists():
                        raise ValueError("SpecNative release archive has no usable install.py")
                    installer_path = roots[0] / "install.py"
                    command[2] = str(installer_path)
                    returncode, stdout, stderr = run_command(command, cwd=str(target_path), timeout=180)
                data = {
                    "action": "install",
                    "executed": True,
                    "repository": REPOSITORY,
                    "version": resolved_version,
                    "installer_url": installer_url,
                    "target": str(target_path),
                    "profile": profile,
                    "returncode": returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                }
                if returncode:
                    return ForgeResult.failure(
                        TOOL,
                        [stderr.strip() or f"Official installer exited with code {returncode}"],
                        timer.elapsed_ms,
                        suggestion="Review the installer output; it may require a clean git worktree or a different profile.",
                    )
                return ForgeResult.success(TOOL, data, timer.elapsed_ms)

            return ForgeResult.failure(TOOL, [f"Unknown action '{action}'"], timer.elapsed_ms)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
            return ForgeResult.failure(
                TOOL,
                [str(exc)],
                timer.elapsed_ms,
                suggestion="Retry the remote read or use a pinned SpecNative release URL when GitHub is unavailable.",
            )


def _add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--action", default="fetch", choices=["fetch", "architecture", "releases", "install"])
    parser.add_argument("--document", default="readme-es", choices=sorted(DOCUMENT_URLS))
    parser.add_argument("--version", default="latest")
    parser.add_argument("--target", default=".")
    parser.add_argument("--profile", default="team", choices=["context", "spec", "team", "platform"])
    parser.add_argument("--include-examples", action="store_true")
    parser.add_argument("--branch", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--repo", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Fetch current SpecNative sources or install an official release", run, _add_args)
