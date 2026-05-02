from __future__ import annotations

"""
gh/api_repo.py — GitHub repository info via REST API (no token required for public repos).

Uses urllib (stdlib only) — no gh CLI, no external deps.
A GITHUB_TOKEN env var is used automatically if present (higher rate limits + private repos).

Actions:
    info        — basic metadata: description, stars, forks, license, topics, language
    languages   — language breakdown (bytes per language)
    contributors — top contributors list
    topics      — repository topics/tags
    readme      — raw README content
    traffic     — views + clones (requires token + push access)
"""

import argparse
import json
import os
import urllib.error
import urllib.request
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "gh.api_repo"
_API = "https://api.github.com"


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(path: str, accept: str | None = None) -> tuple[int, Any]:
    url = f"{_API}{path}" if path.startswith("/") else path
    req = urllib.request.Request(url, headers=_headers())
    if accept:
        req.add_header("Accept", accept)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
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


def _repo_path(owner: str, repo: str) -> str:
    return f"/repos/{owner}/{repo}"


# ── actions ──────────────────────────────────────────────────────────────────

def _info(owner: str, repo: str) -> dict:
    code, data = _get(_repo_path(owner, repo))
    if code != 200:
        raise RuntimeError(data.get("error", f"HTTP {code}"))
    return {
        "full_name":        data.get("full_name"),
        "description":      data.get("description"),
        "homepage":         data.get("homepage"),
        "language":         data.get("language"),
        "stars":            data.get("stargazers_count"),
        "forks":            data.get("forks_count"),
        "watchers":         data.get("watchers_count"),
        "open_issues":      data.get("open_issues_count"),
        "default_branch":   data.get("default_branch"),
        "private":          data.get("private"),
        "archived":         data.get("archived"),
        "fork":             data.get("fork"),
        "license":          (data.get("license") or {}).get("spdx_id"),
        "topics":           data.get("topics", []),
        "created_at":       data.get("created_at"),
        "updated_at":       data.get("updated_at"),
        "pushed_at":        data.get("pushed_at"),
        "size_kb":          data.get("size"),
        "url":              data.get("html_url"),
        "clone_url":        data.get("clone_url"),
        "ssh_url":          data.get("ssh_url"),
    }


def _languages(owner: str, repo: str) -> dict:
    code, data = _get(f"{_repo_path(owner, repo)}/languages")
    if code != 200:
        raise RuntimeError(data.get("error", f"HTTP {code}"))
    total = sum(data.values()) or 1
    return {
        "languages": data,
        "percentages": {lang: round(b / total * 100, 1) for lang, b in data.items()},
    }


def _contributors(owner: str, repo: str, limit: int) -> dict:
    code, data = _get(f"{_repo_path(owner, repo)}/contributors?per_page={limit}&anon=false")
    if code != 200:
        raise RuntimeError(data.get("error", f"HTTP {code}"))
    return {
        "count": len(data),
        "contributors": [
            {"login": c.get("login"), "contributions": c.get("contributions"), "url": c.get("html_url")}
            for c in data
        ],
    }


def _topics(owner: str, repo: str) -> dict:
    code, data = _get(
        f"{_repo_path(owner, repo)}/topics",
        accept="application/vnd.github.mercy-preview+json",
    )
    if code != 200:
        raise RuntimeError(data.get("error", f"HTTP {code}"))
    return {"topics": data.get("names", [])}


def _readme(owner: str, repo: str) -> dict:
    import base64
    code, data = _get(f"{_repo_path(owner, repo)}/readme")
    if code == 404:
        return {"found": False, "content": None}
    if code != 200:
        raise RuntimeError(data.get("error", f"HTTP {code}"))
    content = data.get("content", "")
    encoding = data.get("encoding", "base64")
    if encoding == "base64":
        try:
            content = base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception:
            pass
    return {
        "found":    True,
        "name":     data.get("name"),
        "path":     data.get("path"),
        "size":     data.get("size"),
        "encoding": encoding,
        "content":  content,
    }


def _traffic(owner: str, repo: str) -> dict:
    views_code, views = _get(f"{_repo_path(owner, repo)}/traffic/views")
    clones_code, clones = _get(f"{_repo_path(owner, repo)}/traffic/clones")
    result: dict = {}
    if views_code == 200:
        result["views"] = {"total": views.get("count"), "unique": views.get("uniques")}
    else:
        result["views_error"] = views.get("error", f"HTTP {views_code}")
    if clones_code == 200:
        result["clones"] = {"total": clones.get("count"), "unique": clones.get("uniques")}
    else:
        result["clones_error"] = clones.get("error", f"HTTP {clones_code}")
    return result


# ── public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action: str = "info",
    owner:  str | None = None,
    repo:   str | None = None,
    slug:   str | None = None,   # "owner/repo" shorthand
    limit:  int = 30,
    cwd:    str | None = None,
) -> ForgeResult:
    with Timer() as t:
        # Resolve owner/repo
        if slug:
            parts = slug.split("/", 1)
            if len(parts) != 2:
                return ForgeResult.failure(TOOL, [f"Invalid slug '{slug}', expected 'owner/repo'"], t.elapsed_ms)
            owner, repo = parts
        if not owner or not repo:
            return ForgeResult.failure(
                TOOL, ["Provide --owner + --repo or --slug owner/repo"], t.elapsed_ms
            )

        try:
            if action == "info":
                data = _info(owner, repo)
            elif action == "languages":
                data = _languages(owner, repo)
            elif action == "contributors":
                data = _contributors(owner, repo, limit)
            elif action == "topics":
                data = _topics(owner, repo)
            elif action == "readme":
                data = _readme(owner, repo)
            elif action == "traffic":
                data = _traffic(owner, repo)
            else:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unknown action '{action}'. Use: info | languages | contributors | topics | readme | traffic"],
                    t.elapsed_ms,
                )
        except RuntimeError as exc:
            suggestion = "Set GITHUB_TOKEN for higher rate limits and private repo access" if "rate" in str(exc).lower() or "403" in str(exc) else None
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms, suggestion=suggestion)

        return ForgeResult.success(TOOL, {"owner": owner, "repo": repo, **data}, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="info",
                   choices=["info", "languages", "contributors", "topics", "readme", "traffic"],
                   help="info (default) | languages | contributors | topics | readme | traffic")
    p.add_argument("--slug", default=None, help="owner/repo shorthand, e.g. torvalds/linux")
    p.add_argument("--owner", default=None)
    p.add_argument("--repo", default=None)
    p.add_argument("--limit", type=int, default=30, help="Max contributors to return (default: 30)")


if __name__ == "__main__":
    make_cli(TOOL, "GitHub repository info via REST API (no token needed for public repos)", run, _add_args)
