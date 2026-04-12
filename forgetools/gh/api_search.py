from __future__ import annotations

"""
gh/api_search.py — Search GitHub via REST API (no token needed, higher limits with token).

Uses urllib (stdlib only). GITHUB_TOKEN / GH_TOKEN used automatically if set.

Actions:
    repos   — search repositories by keyword, language, stars, topic
    code    — search code across GitHub (requires token for full results)
    issues  — search issues and pull requests
    users   — search user accounts
    commits — search commits in a specific repo
"""

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "gh.api_search"
_API = "https://api.github.com/search"


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _search(endpoint: str, q: str, per_page: int = 30, sort: str | None = None, order: str = "desc") -> tuple[int, Any]:
    params: dict[str, str] = {"q": q, "per_page": str(per_page)}
    if sort:
        params["sort"] = sort
        params["order"] = order
    url = f"{_API}/{endpoint}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            msg = json.loads(body).get("message", str(e))
        except Exception:
            msg = str(e)
        return e.code, {"error": msg}
    except Exception as e:
        return 0, {"error": str(e)}


# ── query builders ────────────────────────────────────────────────────────────

def _build_repo_query(query: str, language: str | None, topic: str | None,
                      min_stars: int | None, user: str | None, org: str | None) -> str:
    parts = [query]
    if language:
        parts.append(f"language:{language}")
    if topic:
        parts.append(f"topic:{topic}")
    if min_stars is not None:
        parts.append(f"stars:>={min_stars}")
    if user:
        parts.append(f"user:{user}")
    if org:
        parts.append(f"org:{org}")
    return " ".join(parts)


def _build_issue_query(query: str, repo: str | None, state: str | None,
                       label: str | None, author: str | None, issue_type: str) -> str:
    parts = [query, f"type:{issue_type}"]
    if repo:
        parts.append(f"repo:{repo}")
    if state:
        parts.append(f"state:{state}")
    if label:
        parts.append(f"label:{label}")
    if author:
        parts.append(f"author:{author}")
    return " ".join(parts)


# ── formatters ────────────────────────────────────────────────────────────────

def _fmt_repo(r: dict) -> dict:
    return {
        "full_name":   r.get("full_name"),
        "description": r.get("description"),
        "language":    r.get("language"),
        "stars":       r.get("stargazers_count"),
        "forks":       r.get("forks_count"),
        "topics":      r.get("topics", []),
        "url":         r.get("html_url"),
        "updated_at":  r.get("updated_at"),
        "license":     (r.get("license") or {}).get("spdx_id"),
    }


def _fmt_code(c: dict) -> dict:
    return {
        "name":       c.get("name"),
        "path":       c.get("path"),
        "repository": (c.get("repository") or {}).get("full_name"),
        "url":        c.get("html_url"),
        "sha":        c.get("sha", "")[:10],
    }


def _fmt_issue(i: dict) -> dict:
    return {
        "number":     i.get("number"),
        "title":      i.get("title"),
        "state":      i.get("state"),
        "type":       "pr" if "pull_request" in i else "issue",
        "author":     (i.get("user") or {}).get("login"),
        "labels":     [la.get("name") for la in (i.get("labels") or [])],
        "repository": i.get("repository_url", "").replace("https://api.github.com/repos/", ""),
        "url":        i.get("html_url"),
        "created_at": i.get("created_at"),
        "comments":   i.get("comments"),
    }


def _fmt_user(u: dict) -> dict:
    return {
        "login":      u.get("login"),
        "type":       u.get("type"),
        "url":        u.get("html_url"),
        "avatar_url": u.get("avatar_url"),
        "score":      u.get("score"),
    }


def _fmt_commit(c: dict) -> dict:
    commit = c.get("commit") or {}
    author = commit.get("author") or {}
    return {
        "sha":        c.get("sha", "")[:10],
        "message":    (commit.get("message") or "").split("\n")[0],
        "author":     author.get("name"),
        "date":       author.get("date"),
        "repository": (c.get("repository") or {}).get("full_name"),
        "url":        c.get("html_url"),
    }


# ── public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action:    str = "repos",
    query:     str = "",
    language:  str | None = None,
    topic:     str | None = None,
    min_stars: int | None = None,
    user:      str | None = None,
    org:       str | None = None,
    repo:      str | None = None,    # "owner/repo" for code/issue/commit search
    state:     str | None = None,    # open | closed
    label:     str | None = None,
    author:    str | None = None,
    issue_type: str = "issue",       # issue | pr
    sort:      str | None = None,    # stars, forks, updated (repos) | indexed (code) | created, updated, comments (issues)
    order:     str = "desc",
    limit:     int = 20,
    cwd:       str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if not query and action not in ("repos",):
            # allow empty query with filters for repos
            pass

        try:
            if action == "repos":
                q = _build_repo_query(query, language, topic, min_stars, user, org)
                sort_key = sort or "stars"
                code, data = _search("repositories", q, per_page=limit, sort=sort_key, order=order)
                if code != 200:
                    raise RuntimeError(data.get("error", f"HTTP {code}"))
                items = [_fmt_repo(r) for r in data.get("items", [])]
                result = {"total_count": data.get("total_count"), "count": len(items), "query": q, "results": items}

            elif action == "code":
                q = query
                if repo:
                    q = f"{q} repo:{repo}" if q else f"repo:{repo}"
                code, data = _search("code", q, per_page=limit)
                if code != 200:
                    raise RuntimeError(data.get("error", f"HTTP {code}"))
                items = [_fmt_code(c) for c in data.get("items", [])]
                result = {"total_count": data.get("total_count"), "count": len(items), "query": q, "results": items}

            elif action == "issues":
                q = _build_issue_query(query, repo, state, label, author, issue_type)
                sort_key = sort or "updated"
                code, data = _search("issues", q, per_page=limit, sort=sort_key, order=order)
                if code != 200:
                    raise RuntimeError(data.get("error", f"HTTP {code}"))
                items = [_fmt_issue(i) for i in data.get("items", [])]
                result = {"total_count": data.get("total_count"), "count": len(items), "query": q, "results": items}

            elif action == "users":
                code, data = _search("users", query, per_page=limit)
                if code != 200:
                    raise RuntimeError(data.get("error", f"HTTP {code}"))
                items = [_fmt_user(u) for u in data.get("items", [])]
                result = {"total_count": data.get("total_count"), "count": len(items), "query": query, "results": items}

            elif action == "commits":
                if not repo:
                    return ForgeResult.failure(TOOL, ["--repo owner/repo is required for action=commits"], t.elapsed_ms)
                q = f"{query} repo:{repo}" if query else f"repo:{repo}"
                code, data = _search("commits", q, per_page=limit, sort=sort or "committer-date", order=order)
                if code != 200:
                    raise RuntimeError(data.get("error", f"HTTP {code}"))
                items = [_fmt_commit(c) for c in data.get("items", [])]
                result = {"total_count": data.get("total_count"), "count": len(items), "query": q, "results": items}

            else:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unknown action '{action}'. Use: repos | code | issues | users | commits"],
                    t.elapsed_ms,
                )

        except RuntimeError as exc:
            tip = "Set GITHUB_TOKEN for higher rate limits and access to code search"
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms, suggestion=tip)

        return ForgeResult.success(TOOL, result, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action",    default="repos",
                   choices=["repos", "code", "issues", "users", "commits"],
                   help="repos (default) | code | issues | users | commits")
    p.add_argument("--query",     default="", help="Search query string")
    p.add_argument("--language",  default=None, help="Filter repos by programming language")
    p.add_argument("--topic",     default=None, help="Filter repos by topic")
    p.add_argument("--min-stars", type=int, default=None, dest="min_stars")
    p.add_argument("--user",      default=None, help="Filter by GitHub user")
    p.add_argument("--org",       default=None, help="Filter by GitHub org")
    p.add_argument("--repo",      default=None, help="owner/repo for code/issue/commit search")
    p.add_argument("--state",     default=None, choices=["open", "closed"])
    p.add_argument("--label",     default=None)
    p.add_argument("--author",    default=None)
    p.add_argument("--issue-type", default="issue", dest="issue_type", choices=["issue", "pr"])
    p.add_argument("--sort",      default=None)
    p.add_argument("--order",     default="desc", choices=["asc", "desc"])
    p.add_argument("--limit",     type=int, default=20)


if __name__ == "__main__":
    make_cli(TOOL, "Search GitHub repos, code, issues, users via REST API", run, _add_args)
