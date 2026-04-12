from __future__ import annotations

"""
gh/api_releases.py — GitHub releases via REST API (no token needed for public repos).

Uses urllib (stdlib only). GITHUB_TOKEN / GH_TOKEN env vars used automatically
for higher rate limits and private repo access.

Actions:
    list        — all releases with tag, name, draft, prerelease, assets, date
    latest      — latest stable (non-prerelease, non-draft) release
    get         — single release by tag name
    assets      — list downloadable assets for a release
    download    — download a release asset to a local path
    notes       — release notes / body for a specific tag
"""

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "gh.api_releases"
_API = "https://api.github.com"


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(path: str) -> tuple[int, Any]:
    url = f"{_API}{path}" if path.startswith("/") else path
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            msg = json.loads(body).get("message", str(e))
        except Exception:
            msg = str(e)
        return e.code, {"error": msg}
    except Exception as e:
        return 0, {"error": str(e)}


def _release_path(owner: str, repo: str) -> str:
    return f"/repos/{owner}/{repo}/releases"


# ── formatters ────────────────────────────────────────────────────────────────

def _fmt_release(r: dict, include_body: bool = False) -> dict:
    entry: dict = {
        "id":           r.get("id"),
        "tag":          r.get("tag_name"),
        "name":         r.get("name"),
        "draft":        r.get("draft"),
        "prerelease":   r.get("prerelease"),
        "created_at":   r.get("created_at"),
        "published_at": r.get("published_at"),
        "author":       (r.get("author") or {}).get("login"),
        "url":          r.get("html_url"),
        "tarball_url":  r.get("tarball_url"),
        "zipball_url":  r.get("zipball_url"),
        "assets_count": len(r.get("assets", [])),
        "assets": [
            {
                "name":           a.get("name"),
                "size_bytes":     a.get("size"),
                "download_count": a.get("download_count"),
                "content_type":   a.get("content_type"),
                "download_url":   a.get("browser_download_url"),
            }
            for a in r.get("assets", [])
        ],
    }
    if include_body:
        entry["body"] = r.get("body")
    return entry


# ── actions ──────────────────────────────────────────────────────────────────

def _list_releases(owner: str, repo: str, limit: int, include_drafts: bool) -> dict:
    code, data = _get(f"{_release_path(owner, repo)}?per_page={min(limit, 100)}")
    if code != 200:
        raise RuntimeError(data.get("error", f"HTTP {code}"))
    releases = data if isinstance(data, list) else []
    if not include_drafts:
        releases = [r for r in releases if not r.get("draft")]
    return {
        "count":    len(releases),
        "releases": [_fmt_release(r) for r in releases[:limit]],
    }


def _latest(owner: str, repo: str) -> dict:
    code, data = _get(f"{_release_path(owner, repo)}/latest")
    if code == 404:
        return {"found": False}
    if code != 200:
        raise RuntimeError(data.get("error", f"HTTP {code}"))
    return {"found": True, **_fmt_release(data, include_body=True)}


def _get_release(owner: str, repo: str, tag: str) -> dict:
    code, data = _get(f"{_release_path(owner, repo)}/tags/{tag}")
    if code == 404:
        return {"found": False, "tag": tag}
    if code != 200:
        raise RuntimeError(data.get("error", f"HTTP {code}"))
    return {"found": True, **_fmt_release(data, include_body=True)}


def _assets(owner: str, repo: str, tag: str) -> dict:
    r = _get_release(owner, repo, tag)
    if not r.get("found"):
        raise RuntimeError(f"Release '{tag}' not found")
    return {"tag": tag, "assets_count": r["assets_count"], "assets": r["assets"]}


def _download(owner: str, repo: str, tag: str, asset_name: str, dest: str) -> dict:
    r = _get_release(owner, repo, tag)
    if not r.get("found"):
        raise RuntimeError(f"Release '{tag}' not found")

    asset = next((a for a in r["assets"] if a["name"] == asset_name), None)
    if asset is None:
        available = [a["name"] for a in r["assets"]]
        raise RuntimeError(f"Asset '{asset_name}' not found in release '{tag}'. Available: {available}")

    url = asset["download_url"]
    dest_path = Path(dest) / asset_name if Path(dest).is_dir() else Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=120) as resp:
        content = resp.read()

    dest_path.write_bytes(content)
    return {
        "downloaded":  True,
        "asset":       asset_name,
        "tag":         tag,
        "size_bytes":  len(content),
        "dest":        str(dest_path.resolve()),
    }


def _notes(owner: str, repo: str, tag: str) -> dict:
    r = _get_release(owner, repo, tag)
    if not r.get("found"):
        raise RuntimeError(f"Release '{tag}' not found")
    return {"tag": tag, "name": r.get("name"), "body": r.get("body")}


# ── public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action:        str = "list",
    owner:         str | None = None,
    repo:          str | None = None,
    slug:          str | None = None,
    tag:           str | None = None,
    asset:         str | None = None,    # asset file name for download
    dest:          str = ".",            # download destination
    limit:         int = 20,
    include_drafts: bool = False,
    cwd:           str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if slug:
            parts = slug.split("/", 1)
            if len(parts) != 2:
                return ForgeResult.failure(TOOL, [f"Invalid slug '{slug}'"], t.elapsed_ms)
            owner, repo = parts
        if not owner or not repo:
            return ForgeResult.failure(TOOL, ["Provide --owner + --repo or --slug owner/repo"], t.elapsed_ms)

        try:
            if action == "list":
                data = _list_releases(owner, repo, limit, include_drafts)
            elif action == "latest":
                data = _latest(owner, repo)
            elif action == "get":
                if not tag:
                    return ForgeResult.failure(TOOL, ["--tag is required for action=get"], t.elapsed_ms)
                data = _get_release(owner, repo, tag)
            elif action == "assets":
                if not tag:
                    return ForgeResult.failure(TOOL, ["--tag is required for action=assets"], t.elapsed_ms)
                data = _assets(owner, repo, tag)
            elif action == "download":
                if not tag or not asset:
                    return ForgeResult.failure(TOOL, ["--tag and --asset are required for action=download"], t.elapsed_ms)
                data = _download(owner, repo, tag, asset, dest)
            elif action == "notes":
                if not tag:
                    return ForgeResult.failure(TOOL, ["--tag is required for action=notes"], t.elapsed_ms)
                data = _notes(owner, repo, tag)
            else:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unknown action '{action}'. Use: list | latest | get | assets | download | notes"],
                    t.elapsed_ms,
                )
        except RuntimeError as exc:
            tip = "Set GITHUB_TOKEN for higher rate limits and private repo access"
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms, suggestion=tip)

        return ForgeResult.success(TOOL, {"owner": owner, "repo": repo, **data}, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="list",
                   choices=["list", "latest", "get", "assets", "download", "notes"],
                   help="list (default) | latest | get | assets | download | notes")
    p.add_argument("--slug",   default=None, help="owner/repo e.g. cli/cli")
    p.add_argument("--owner",  default=None)
    p.add_argument("--repo",   default=None)
    p.add_argument("--tag",    default=None, help="Release tag, e.g. v2.0.0")
    p.add_argument("--asset",  default=None, help="Asset filename to download")
    p.add_argument("--dest",   default=".",  help="Download destination path (default: cwd)")
    p.add_argument("--limit",  type=int, default=20)
    p.add_argument("--include-drafts", action="store_true", dest="include_drafts")


if __name__ == "__main__":
    make_cli(TOOL, "GitHub releases via REST API (no token needed for public repos)", run, _add_args)
