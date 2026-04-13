from __future__ import annotations

"""
java/maven_central.py — Interact with Maven Central Repository.

All calls use the public REST API (no token required):
  Search API  : https://search.maven.org/solrsearch/select  (Solr-based)
  Artifact CDN: https://repo1.maven.org/maven2/

Actions:
    search      — full-text or field search for artifacts
    info        — summary of an artifact (latest version, size, timestamps)
    versions    — all published versions for a groupId:artifactId
    latest      — latest version details + checksums in one call
    checksums   — SHA1 / SHA256 / MD5 for a specific groupId:artifactId:version
    pom         — fetch raw POM XML for a specific version
    dependency  — emit Maven + Gradle dependency snippets
    browse      — list artifacts in a groupId namespace
"""

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "java.maven_central"

_SEARCH_URL  = "https://search.maven.org/solrsearch/select"
_REPO_URL    = "https://repo1.maven.org/maven2"
_TIMEOUT     = 20

_DEFAULT_ROWS = 20
_MAX_ROWS     = 200


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _get(url: str, params: dict | None = None, timeout: int = _TIMEOUT) -> dict | str:
    """GET request; returns parsed JSON dict or raw string."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                "User-Agent": "forgetools/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        ct   = resp.headers.get("Content-Type", "")
        if "json" in ct:
            return json.loads(body)
        return body.decode("utf-8", errors="replace")


def _get_bytes(url: str, timeout: int = _TIMEOUT) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "forgetools/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _try_get(url: str, params: dict | None = None) -> tuple[bool, dict | str]:
    try:
        return True, _get(url, params)
    except urllib.error.HTTPError as exc:
        return False, {"http_error": exc.code, "url": url}
    except Exception as exc:
        return False, {"error": str(exc), "url": url}


# ── coordinate helpers ────────────────────────────────────────────────────────

def _parse_coords(coords: str) -> tuple[str, str, str | None]:
    """Parse 'groupId:artifactId[:version]' into (group, artifact, version|None)."""
    parts = coords.split(":", 2)
    if len(parts) < 2:
        raise ValueError(f"Coordinates must be 'groupId:artifactId[:version]', got: {coords!r}")
    g = parts[0].strip()
    a = parts[1].strip()
    v = parts[2].strip() if len(parts) > 2 else None
    return g, a, v


def _artifact_path(group_id: str, artifact_id: str, version: str,
                   packaging: str = "jar", classifier: str = "") -> str:
    """Return the relative path under repo1.maven.org for an artifact."""
    group_path = group_id.replace(".", "/")
    name = f"{artifact_id}-{version}"
    if classifier:
        name += f"-{classifier}"
    name += f".{packaging}"
    return f"{group_path}/{artifact_id}/{version}/{name}"


def _artifact_url(group_id: str, artifact_id: str, version: str,
                  packaging: str = "jar", classifier: str = "") -> str:
    return f"{_REPO_URL}/{_artifact_path(group_id, artifact_id, version, packaging, classifier)}"


# ── actions ───────────────────────────────────────────────────────────────────

def _search(
    query: str,
    group_id: str | None,
    artifact_id: str | None,
    packaging: str | None,
    rows: int,
) -> dict:
    """Full-text or field-based search."""
    q_parts: list[str] = []
    if query:
        q_parts.append(query)
    if group_id:
        q_parts.append(f"g:{group_id}")
    if artifact_id:
        q_parts.append(f"a:{artifact_id}")
    if packaging:
        q_parts.append(f"p:{packaging}")

    if not q_parts:
        raise ValueError("Provide at least one of: --query, --group-id, --artifact-id")

    q = " AND ".join(q_parts)
    params = {"q": q, "rows": min(rows, _MAX_ROWS), "wt": "json"}

    ok, resp = _try_get(_SEARCH_URL, params)
    if not ok:
        return resp  # type: ignore[return-value]

    docs = resp.get("response", {}).get("docs", [])  # type: ignore[union-attr]
    num_found = resp.get("response", {}).get("numFound", 0)

    results = []
    for d in docs:
        results.append({
            "group_id":       d.get("g"),
            "artifact_id":    d.get("a"),
            "latest_version": d.get("latestVersion"),
            "packaging":      d.get("p"),
            "repository_id":  d.get("repositoryId"),
            "timestamp":      d.get("timestamp"),
            "version_count":  d.get("versionCount"),
            "tags":           d.get("tags", []),
        })

    return {
        "query":     q,
        "num_found": num_found,
        "returned":  len(results),
        "results":   results,
    }


def _info(group_id: str, artifact_id: str) -> dict:
    """Artifact summary: packaging, latest version, timestamps, description."""
    params = {
        "q":    f"g:{group_id} AND a:{artifact_id}",
        "rows": 1,
        "wt":   "json",
    }
    ok, resp = _try_get(_SEARCH_URL, params)
    if not ok:
        return resp  # type: ignore[return-value]

    docs = resp.get("response", {}).get("docs", [])  # type: ignore[union-attr]
    if not docs:
        return {"ok": False, "error": f"Artifact {group_id}:{artifact_id} not found"}

    d = docs[0]
    latest = d.get("latestVersion", "")

    result = {
        "group_id":         d.get("g"),
        "artifact_id":      d.get("a"),
        "latest_version":   latest,
        "packaging":        d.get("p"),
        "version_count":    d.get("versionCount"),
        "last_updated_ts":  d.get("timestamp"),
        "tags":             d.get("tags", []),
        "repository_id":    d.get("repositoryId"),
    }

    # Enrich with latest POM description if possible
    if latest:
        try:
            pom_url = _artifact_url(group_id, artifact_id, latest, "pom")
            ok2, pom_text = _try_get(pom_url)
            if ok2 and isinstance(pom_text, str):
                import re
                m = re.search(r"<description>(.*?)</description>", pom_text, re.DOTALL)
                if m:
                    result["description"] = m.group(1).strip()
                m2 = re.search(r"<url>(.*?)</url>", pom_text)
                if m2:
                    result["url"] = m2.group(1).strip()
                m3 = re.search(r"<scm>.*?<url>(.*?)</url>.*?</scm>", pom_text, re.DOTALL)
                if m3:
                    result["scm_url"] = m3.group(1).strip()
        except Exception:
            pass  # enrichment is best-effort

    return result


def _versions(group_id: str, artifact_id: str, rows: int) -> dict:
    """List all published versions, newest first."""
    params = {
        "q":    f"g:{group_id} AND a:{artifact_id}",
        "core": "gav",
        "rows": min(rows, _MAX_ROWS),
        "wt":   "json",
    }
    ok, resp = _try_get(_SEARCH_URL, params)
    if not ok:
        return resp  # type: ignore[return-value]

    docs      = resp.get("response", {}).get("docs", [])  # type: ignore[union-attr]
    num_found = resp.get("response", {}).get("numFound", 0)

    versions = [
        {
            "version":   d.get("v"),
            "packaging": d.get("p"),
            "timestamp": d.get("timestamp"),
        }
        for d in docs
    ]

    return {
        "group_id":    group_id,
        "artifact_id": artifact_id,
        "num_found":   num_found,
        "returned":    len(versions),
        "versions":    versions,
    }


def _checksums(
    group_id: str, artifact_id: str, version: str,
    packaging: str, classifier: str,
) -> dict:
    """Fetch SHA1 / SHA256 / MD5 checksums for a specific artifact."""
    base_url = _artifact_url(group_id, artifact_id, version, packaging, classifier)

    result: dict = {
        "group_id":    group_id,
        "artifact_id": artifact_id,
        "version":     version,
        "packaging":   packaging,
        "classifier":  classifier or None,
        "artifact_url": base_url,
    }

    for ext, key in [(".sha1", "sha1"), (".sha256", "sha256"), (".md5", "md5")]:
        url = base_url + ext
        try:
            data = _get_bytes(url, timeout=10)
            # checksum files may contain filename suffix: "<hash>  filename"
            value = data.decode("utf-8", errors="replace").split()[0].strip()
            result[key] = value
        except urllib.error.HTTPError as exc:
            result[key] = f"HTTP {exc.code}" if exc.code != 404 else "not published"
        except Exception as exc:
            result[key] = f"error: {exc}"

    # Also report Content-Length (artifact size) from HEAD
    try:
        req = urllib.request.Request(base_url, method="HEAD",
                                     headers={"User-Agent": "forgetools/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            result["content_length_bytes"] = int(r.headers.get("Content-Length", 0) or 0)
            result["last_modified"]        = r.headers.get("Last-Modified", "")
    except Exception:
        pass

    return result


def _latest(group_id: str, artifact_id: str, packaging: str) -> dict:
    """Latest version + checksums in one call."""
    info = _info(group_id, artifact_id)
    if not info.get("latest_version"):
        return info

    version = info["latest_version"]
    csums   = _checksums(group_id, artifact_id, version, packaging, "")

    return {**info, "checksums": csums}


def _pom(group_id: str, artifact_id: str, version: str) -> dict:
    """Fetch raw POM XML for a specific version."""
    url = _artifact_url(group_id, artifact_id, version, "pom")
    ok, resp = _try_get(url)
    if not ok:
        return resp  # type: ignore[return-value]
    return {
        "group_id":    group_id,
        "artifact_id": artifact_id,
        "version":     version,
        "pom_url":     url,
        "pom_xml":     resp if isinstance(resp, str) else json.dumps(resp),
    }


def _dependency(group_id: str, artifact_id: str, version: str, packaging: str) -> dict:
    """Emit Maven and Gradle dependency snippets."""
    scope_hint  = "test" if "test" in artifact_id.lower() else "compile"
    maven_scope = "<scope>test</scope>\n    " if scope_hint == "test" else ""

    maven = (
        f"<dependency>\n"
        f"    <groupId>{group_id}</groupId>\n"
        f"    <artifactId>{artifact_id}</artifactId>\n"
        f"    <version>{version}</version>\n"
        f"    {maven_scope}"
        f"</dependency>"
    ).rstrip()

    if packaging == "pom":
        maven = (
            f"<dependency>\n"
            f"    <groupId>{group_id}</groupId>\n"
            f"    <artifactId>{artifact_id}</artifactId>\n"
            f"    <version>{version}</version>\n"
            f"    <type>pom</type>\n"
            f"    {maven_scope}"
            f"</dependency>"
        ).rstrip()

    groovy_cfg  = "testImplementation" if scope_hint == "test" else "implementation"
    gradle      = f'{groovy_cfg} "{group_id}:{artifact_id}:{version}"'
    gradle_kts  = f'{groovy_cfg}("{group_id}:{artifact_id}:{version}")'

    return {
        "group_id":     group_id,
        "artifact_id":  artifact_id,
        "version":      version,
        "packaging":    packaging,
        "maven_xml":    maven,
        "gradle":       gradle,
        "gradle_kotlin": gradle_kts,
        "sbt":          f'"{group_id}" % "{artifact_id}" % "{version}"',
        "ivy":          f'<dependency org="{group_id}" name="{artifact_id}" rev="{version}"/>',
    }


def _browse(group_id: str, rows: int) -> dict:
    """List artifacts in a groupId namespace."""
    params = {
        "q":    f"g:{group_id}",
        "rows": min(rows, _MAX_ROWS),
        "wt":   "json",
    }
    ok, resp = _try_get(_SEARCH_URL, params)
    if not ok:
        return resp  # type: ignore[return-value]

    docs      = resp.get("response", {}).get("docs", [])  # type: ignore[union-attr]
    num_found = resp.get("response", {}).get("numFound", 0)

    artifacts = [
        {
            "artifact_id":    d.get("a"),
            "latest_version": d.get("latestVersion"),
            "packaging":      d.get("p"),
            "version_count":  d.get("versionCount"),
            "last_updated_ts": d.get("timestamp"),
        }
        for d in docs
    ]

    return {
        "group_id":    group_id,
        "num_found":   num_found,
        "returned":    len(artifacts),
        "artifacts":   artifacts,
    }


# ── public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action:      str       = "search",
    query:       str       = "",
    coords:      str       = "",        # groupId:artifactId[:version]
    group_id:    str       = "",
    artifact_id: str       = "",
    version:     str       = "",
    packaging:   str       = "jar",
    classifier:  str       = "",
    rows:        int       = _DEFAULT_ROWS,
    cwd:         str | None = None,
) -> ForgeResult:
    with Timer() as t:
        try:
            # --coords shorthand expands into group_id / artifact_id / version
            if coords:
                g, a, v = _parse_coords(coords)
                if not group_id:
                    group_id = g
                if not artifact_id:
                    artifact_id = a
                if not version and v:
                    version = v

            if action == "search":
                data = _search(query, group_id or None, artifact_id or None,
                               packaging if packaging != "jar" else None, rows)

            elif action == "info":
                if not group_id or not artifact_id:
                    return ForgeResult.failure(
                        TOOL,
                        ["--group-id and --artifact-id (or --coords) are required for info"],
                        t.elapsed_ms,
                    )
                data = _info(group_id, artifact_id)

            elif action == "versions":
                if not group_id or not artifact_id:
                    return ForgeResult.failure(
                        TOOL,
                        ["--group-id and --artifact-id (or --coords) are required for versions"],
                        t.elapsed_ms,
                    )
                data = _versions(group_id, artifact_id, rows)

            elif action == "latest":
                if not group_id or not artifact_id:
                    return ForgeResult.failure(
                        TOOL,
                        ["--group-id and --artifact-id (or --coords) are required for latest"],
                        t.elapsed_ms,
                    )
                data = _latest(group_id, artifact_id, packaging)

            elif action == "checksums":
                if not group_id or not artifact_id or not version:
                    return ForgeResult.failure(
                        TOOL,
                        ["--group-id, --artifact-id, --version (or --coords g:a:v) are required"],
                        t.elapsed_ms,
                    )
                data = _checksums(group_id, artifact_id, version, packaging, classifier)

            elif action == "pom":
                if not group_id or not artifact_id or not version:
                    return ForgeResult.failure(
                        TOOL,
                        ["--group-id, --artifact-id, --version (or --coords g:a:v) are required for pom"],
                        t.elapsed_ms,
                    )
                data = _pom(group_id, artifact_id, version)

            elif action == "dependency":
                if not group_id or not artifact_id:
                    return ForgeResult.failure(
                        TOOL,
                        ["--group-id and --artifact-id (+ optionally --version) are required"],
                        t.elapsed_ms,
                    )
                # If no version supplied, resolve latest first
                if not version:
                    info = _info(group_id, artifact_id)
                    version = info.get("latest_version", "LATEST")
                data = _dependency(group_id, artifact_id, version, packaging)

            elif action == "browse":
                if not group_id:
                    return ForgeResult.failure(
                        TOOL,
                        ["--group-id is required for browse"],
                        t.elapsed_ms,
                    )
                data = _browse(group_id, rows)

            else:
                return ForgeResult.failure(
                    TOOL,
                    [f"Unknown action '{action}'. "
                     f"Use: search | info | versions | latest | checksums | pom | dependency | browse"],
                    t.elapsed_ms,
                )

        except Exception as exc:
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action",      default="search",
                   choices=["search", "info", "versions", "latest",
                            "checksums", "pom", "dependency", "browse"])
    p.add_argument("--query",       default="",
                   help="Full-text search query (action=search)")
    p.add_argument("--coords",      default="",
                   help="Coordinates shorthand: groupId:artifactId[:version]")
    p.add_argument("--group-id",    dest="group_id",    default="",
                   help="Maven groupId  (e.g. org.springframework.boot)")
    p.add_argument("--artifact-id", dest="artifact_id", default="",
                   help="Maven artifactId (e.g. spring-boot-starter-web)")
    p.add_argument("--version",     default="",
                   help="Specific version (required for checksums/pom)")
    p.add_argument("--packaging",   default="jar",
                   help="Packaging type: jar | pom | war | aar | ... (default: jar)")
    p.add_argument("--classifier",  default="",
                   help="Artifact classifier: sources | javadoc | tests | ...")
    p.add_argument("--rows",        type=int, default=_DEFAULT_ROWS,
                   help=f"Max results to return (default {_DEFAULT_ROWS}, max {_MAX_ROWS})")


if __name__ == "__main__":
    make_cli(
        TOOL,
        "Search Maven Central: artifacts, versions, checksums, POM, dependency snippets",
        run, _add_args,
    )
