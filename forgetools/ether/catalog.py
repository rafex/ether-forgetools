from __future__ import annotations

"""
ether/catalog.py — Ether module catalog for agents.

Fetches live data from ether-deployment-hub (public GitHub repo).
Caches locally for 1 hour in ~/.cache/forgetools/.

Actions:
    list    — all modules with version, status, description
    search  — filter by name or keyword
    deps    — dependency chain for a module
    pom     — Maven <dependency> XML snippet
    order   — publish order (topology)
    refresh — force cache invalidation

Source files (fetched):
    releases/manifest.json          → versions, deps, deploy order
    docs/maven-central-status.json  → deployed flag, latestVersion, artifactUrl
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "ether.catalog"

# ── Remote URLs ───────────────────────────────────────────────────────────────

_RAW = "https://raw.githubusercontent.com/rafex/ether-deployment-hub/main"
_MANIFEST_URL = f"{_RAW}/releases/manifest.json"
_STATUS_URL   = f"{_RAW}/docs/maven-central-status.json"

# ── Local cache ───────────────────────────────────────────────────────────────

_CACHE_DIR  = Path.home() / ".cache" / "forgetools"
_CACHE_MAN  = _CACHE_DIR / "ether-manifest.json"
_CACHE_STAT = _CACHE_DIR / "ether-status.json"
_CACHE_TTL  = 3600  # 1 hour

# ── Embedded descriptions (sourced from ether.rafex.io) ───────────────────────

_DESCRIPTIONS: dict[str, str] = {
    "ether-parent":             "Parent POM and BOM managing all external dependency versions across the ecosystem",
    "ether-config":             "Typed configuration entry points and composition APIs for Ether applications",
    "ether-crypto":             "Cryptographic utilities: hashing, encoding, secure random, key generation",
    "ether-database-core":      "Database contracts: DatabaseClient interface and RowMapper abstraction",
    "ether-jdbc":               "JDBC implementation of ether-database-core abstractions",
    "ether-database-postgres":  "PostgreSQL error classification, SQL state constants, and pg-specific helpers",
    "ether-json":               "JsonCodec interface built on Jackson for flexible and pluggable serialization",
    "ether-jwt":                "Lightweight cryptographic primitives for JWT: HS256, RS256, ES256 token operations",
    "ether-observability-core": "Health checks, request ID generation, timing recording, and metrics contracts",
    "ether-http-core":          "Core HTTP contracts: HttpExchange, HttpHandler, Middleware, routing abstractions",
    "ether-http-security":      "CORS policies, security headers, IP allowlisting, and rate limiting configurations",
    "ether-http-problem":       "RFC 7807 Problem Details error response formatting for HTTP APIs",
    "ether-http-openapi":       "Programmatic OpenAPI 3.1 specification builder — describe your API in Java code",
    "ether-http-client":        "Outbound HTTP client built on java.net.http with retry and JSON parsing support",
    "ether-logging-core":       "Logging contracts and structured log support for Ether applications",
    "ether-ai-core":            "AI provider contracts: ChatClient, CompletionRequest, Message abstractions",
    "ether-ai-openai":          "OpenAI provider implementation for ether-ai-core (chat completions, embeddings)",
    "ether-ai-deepseek":        "DeepSeek provider implementation for ether-ai-core",
    "ether-http-jetty12":       "Production-ready HTTP server integrating all ether-http-* modules via Jetty 12",
    "ether-websocket-core":     "Transport-agnostic WebSocket contracts: Session, MessageHandler, frame types",
    "ether-websocket-jetty12":  "Jetty 12-based WebSocket server implementation of ether-websocket-core",
    "ether-webhook":            "Webhook delivery, signing (HMAC-SHA256), and signature verification support",
    "ether-glowroot-jetty12":   "Glowroot APM instrumentation plugin for Jetty 12 — zero code modification required",
}

# ── Fetch + cache ─────────────────────────────────────────────────────────────

def _fetch_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) < _CACHE_TTL


def _load_cached(path: Path, url: str, force: bool) -> dict | list:
    if not force and _is_fresh(path):
        return json.loads(path.read_text())
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = _fetch_json(url)
    path.write_text(json.dumps(data, indent=2))
    return data


def _load_catalog(force: bool = False) -> tuple[dict, dict]:
    """Returns (manifest_by_name, status_by_name)."""
    manifest_raw: dict = _load_cached(_CACHE_MAN,  _MANIFEST_URL, force)
    status_raw:   list = _load_cached(_CACHE_STAT, _STATUS_URL,   force)

    manifest_by_name: dict[str, dict] = {
        m["name"]: m for m in manifest_raw.get("modules", [])
    }
    status_by_name: dict[str, dict] = {
        s["module"]: s for s in status_raw
    }
    return manifest_by_name, status_by_name


def _merge(name: str, man: dict, stat: dict) -> dict:
    s = stat.get(name, {})
    return {
        "name":        name,
        "groupId":     man.get("groupId", s.get("groupId", "")),
        "artifactId":  man.get("artifactId", s.get("artifactId", name)),
        "version":     s.get("latestVersion") or man.get("currentVersion", ""),
        "deployed":    s.get("deployed", man.get("published", False)),
        "description": _DESCRIPTIONS.get(name, ""),
        "dependencies": man.get("dependencies", []),
        "artifactUrl": s.get("artifactUrl", ""),
        "mavenCoord":  f"{man.get('groupId', '')}:{man.get('artifactId', name)}",
    }


# ── Actions ───────────────────────────────────────────────────────────────────

def _do_list(man: dict, stat: dict, deployed_only: bool) -> dict:
    modules = [
        _merge(name, m, stat)
        for name, m in man.items()
        if not deployed_only or stat.get(name, {}).get("deployed", m.get("published"))
    ]
    return {
        "total":    len(modules),
        "modules":  modules,
        "source":   _MANIFEST_URL,
    }


def _do_search(man: dict, stat: dict, query: str) -> dict:
    q = query.lower()
    results = []
    for name, m in man.items():
        merged = _merge(name, m, stat)
        haystack = f"{name} {merged['description']} {merged['groupId']}".lower()
        if q in haystack:
            results.append(merged)
    return {"query": query, "count": len(results), "modules": results}


def _resolve_deps(name: str, man: dict, stat: dict, seen: set[str] | None = None) -> list[dict]:
    if seen is None:
        seen = set()
    if name in seen:
        return []
    seen.add(name)
    result = []
    for dep in man.get(name, {}).get("dependencies", []):
        result.append(_merge(dep, man.get(dep, {}), stat))
        result.extend(_resolve_deps(dep, man, stat, seen))
    return result


def _do_deps(man: dict, stat: dict, module: str) -> dict:
    if module not in man:
        # fuzzy match
        matches = [n for n in man if module in n]
        if len(matches) == 1:
            module = matches[0]
        elif matches:
            return {"error": f"Ambiguous: {matches}"}
        else:
            return {"error": f"Module '{module}' not found"}

    direct = [
        _merge(d, man.get(d, {}), stat)
        for d in man[module].get("dependencies", [])
    ]
    transitive = _resolve_deps(module, man, stat)

    return {
        "module":     module,
        "direct":     direct,
        "transitive": transitive,
        "total_deps": len(set(d["name"] for d in transitive)),
    }


def _do_pom(man: dict, stat: dict, module: str) -> dict:
    if module not in man:
        matches = [n for n in man if module in n]
        if len(matches) == 1:
            module = matches[0]
        elif matches:
            return {"error": f"Ambiguous: {matches}"}
        else:
            return {"error": f"Module '{module}' not found"}

    m = _merge(module, man[module], stat)
    snippet = (
        f"<dependency>\n"
        f"    <groupId>{m['groupId']}</groupId>\n"
        f"    <artifactId>{m['artifactId']}</artifactId>\n"
        f"    <version>{m['version']}</version>\n"
        f"</dependency>"
    )
    return {
        "module":      module,
        "groupId":     m["groupId"],
        "artifactId":  m["artifactId"],
        "version":     m["version"],
        "deployed":    m["deployed"],
        "description": m["description"],
        "pom_snippet": snippet,
        "artifactUrl": m["artifactUrl"],
    }


def _do_order(man: dict, stat: dict) -> dict:
    raw: dict = json.loads(_CACHE_MAN.read_text()) if _CACHE_MAN.exists() else {}
    order = raw.get("deployOrder", list(man.keys()))
    return {
        "deploy_order": [
            {
                "position": i + 1,
                "name":     name,
                "version":  stat.get(name, {}).get("latestVersion")
                            or man.get(name, {}).get("currentVersion", ""),
            }
            for i, name in enumerate(order)
        ],
        "total": len(order),
    }


# ── run() ─────────────────────────────────────────────────────────────────────

def run(
    *,
    action: str = "list",
    query: str | None = None,
    module: str | None = None,
    deployed_only: bool = False,
    refresh: bool = False,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if action == "refresh":
            refresh = True
            action  = "list"

        try:
            man, stat = _load_catalog(force=refresh)
        except Exception as e:
            return ForgeResult.failure(
                TOOL,
                [f"Failed to fetch Ether catalog: {e}"],
                t.elapsed_ms,
                suggestion=(
                    "Check internet connection. "
                    "Repo: https://github.com/rafex/ether-deployment-hub"
                ),
            )

        if action == "list":
            data = _do_list(man, stat, deployed_only)

        elif action == "search":
            if not query:
                return ForgeResult.failure(
                    TOOL, ["--query is required for action=search"], t.elapsed_ms
                )
            data = _do_search(man, stat, query)

        elif action == "deps":
            if not module:
                return ForgeResult.failure(
                    TOOL, ["--module is required for action=deps"], t.elapsed_ms
                )
            data = _do_deps(man, stat, module)
            if "error" in data:
                return ForgeResult.failure(
                    TOOL, [data["error"]], t.elapsed_ms,
                    suggestion="Run action=list to see available modules",
                )

        elif action == "pom":
            if not module:
                return ForgeResult.failure(
                    TOOL, ["--module is required for action=pom"], t.elapsed_ms
                )
            data = _do_pom(man, stat, module)
            if "error" in data:
                return ForgeResult.failure(
                    TOOL, [data["error"]], t.elapsed_ms,
                    suggestion="Run action=search --query <term> to find the module name",
                )

        elif action == "order":
            data = _do_order(man, stat)

        else:
            return ForgeResult.failure(
                TOOL,
                [f"Unknown action '{action}'. Valid: list | search | deps | pom | order | refresh"],
                t.elapsed_ms,
            )

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--action", default="list",
        choices=["list", "search", "deps", "pom", "order", "refresh"],
        help=(
            "list: all modules | search: filter by keyword | "
            "deps: dependency chain | pom: Maven XML snippet | "
            "order: deploy order | refresh: clear cache and reload"
        ),
    )
    p.add_argument("--query",   "-q", default=None,
                   help="Search query (for action=search)")
    p.add_argument("--module",  "-m", default=None,
                   help="Module name, partial match ok (for action=deps or action=pom)")
    p.add_argument("--deployed-only", action="store_true", dest="deployed_only",
                   help="Only show modules deployed to Maven Central (for action=list)")
    p.add_argument("--refresh", action="store_true",
                   help="Force cache refresh from GitHub")


if __name__ == "__main__":
    make_cli(
        TOOL,
        "Ether module catalog — list, search, deps, pom snippets",
        run,
        _add_args,
    )
