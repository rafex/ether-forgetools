from __future__ import annotations

"""
net/http_request.py — HTTP client with auto-backend selection.

Backends tried in order (unless --backend is specified):
  1. curl   — widest feature support, best for binary/streaming
  2. wget   — fallback if curl unavailable
  3. python — stdlib urllib, always available, no subprocess

Supports: GET POST PUT PATCH DELETE HEAD OPTIONS
          JSON body, form data, custom headers, basic auth, bearer token,
          redirect following, TLS skip, response to file, timeout.

Usage:
    forge net http --url https://api.example.com/users
    forge net http --url https://api.example.com/users --method POST --body '{"name":"rafex"}'
    forge net http --url https://api.example.com/data  --header "X-Key: abc" --bearer mytoken
    forge net http --url https://example.com/file.zip  --output /tmp/file.zip
"""

import argparse
import json
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "net.http_request"

_TRUNCATE_BODY = 8192  # chars kept in response body field


# ── Helpers ───────────────────────────────────────────────────────────────────

def _try_json(text: str) -> dict | list | None:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _truncate(s: str, n: int = _TRUNCATE_BODY) -> str:
    return s[:n] + f"\n…[truncated {len(s) - n} chars]" if len(s) > n else s


def _parse_headers(raw: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for h in raw or []:
        if ":" in h:
            k, _, v = h.partition(":")
            result[k.strip()] = v.strip()
    return result


def _auth_header(auth: str | None, bearer: str | None) -> dict[str, str]:
    if bearer:
        return {"Authorization": f"Bearer {bearer}"}
    if auth and ":" in auth:
        import base64
        return {"Authorization": "Basic " + base64.b64encode(auth.encode()).decode()}
    return {}


def _available(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# ── curl backend ──────────────────────────────────────────────────────────────

def _curl(url: str, method: str, headers: dict, body: str | None,
          form: str | None, timeout: int, follow: bool, insecure: bool,
          output: str | None) -> dict:
    cmd = [
        "curl", "-s",
        "-w", "\n__STATUS__%{http_code}__CT__%{content_type}__",
        "-X", method, "--max-time", str(timeout),
        "-D", "-",          # dump response headers inline
    ]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    if body:
        cmd += ["-d", body]
        if "Content-Type" not in headers:
            cmd += ["-H", "Content-Type: application/json"]
    if form:
        cmd += ["-F", form]
    if follow:
        cmd.append("-L")
    if insecure:
        cmd.append("-k")
    if output:
        cmd += ["-o", output]
    cmd.append(url)

    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    except subprocess.TimeoutExpired:
        return {"error": "curl timed out"}
    except FileNotFoundError:
        return {"error": "curl not found"}

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    raw = proc.stdout

    # Extract -w sentinel appended at end
    m = re.search(r"\n__STATUS__(\d+)__CT__([^_]*)__\s*$", raw)
    status = int(m.group(1)) if m else 0
    content_type = m.group(2).strip() if m else ""
    raw_no_sentinel = raw[:m.start()] if m else raw

    # Split HTTP headers from body (curl -D - prepends them)
    sections = re.split(r"\r?\n\r?\n", raw_no_sentinel, maxsplit=2)
    resp_headers: dict[str, str] = {}
    body_text = ""
    if len(sections) >= 2:
        for line in sections[0].splitlines()[1:]:   # skip HTTP/x status line
            if ":" in line:
                hk, _, hv = line.partition(":")
                resp_headers[hk.strip()] = hv.strip()
        body_text = "\n\n".join(sections[1:]).strip()
    else:
        body_text = raw_no_sentinel.strip()

    return {
        "status": status, "content_type": content_type,
        "headers": resp_headers, "body": _truncate(body_text),
        "body_json": _try_json(body_text), "elapsed_ms": elapsed_ms,
        "backend": "curl", "saved_to": output,
    }


# ── wget backend ──────────────────────────────────────────────────────────────

def _wget(url: str, method: str, headers: dict, body: str | None,
          timeout: int, follow: bool, insecure: bool, output: str | None) -> dict:
    cmd = [
        "wget", "-q", "-O", output or "-",
        "--server-response", "--timeout", str(timeout),
        "--method", method,
    ]
    for k, v in headers.items():
        cmd += ["--header", f"{k}: {v}"]
    if body:
        cmd += ["--body-data", body]
        if "Content-Type" not in headers:
            cmd += ["--header", "Content-Type: application/json"]
    if not follow:
        cmd += ["--max-redirect=0"]
    if insecure:
        cmd.append("--no-check-certificate")
    cmd.append(url)

    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    except subprocess.TimeoutExpired:
        return {"error": "wget timed out"}
    except FileNotFoundError:
        return {"error": "wget not found"}

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    status = 0
    resp_headers: dict[str, str] = {}
    for line in proc.stderr.splitlines():
        m = re.match(r"\s*HTTP/[\d.]+ (\d+)", line)
        if m:
            status = int(m.group(1))
        elif ":" in line and line.startswith("  "):
            hk, _, hv = line.strip().partition(":")
            resp_headers[hk.strip()] = hv.strip()

    body_text = proc.stdout.strip()
    return {
        "status": status, "content_type": resp_headers.get("Content-Type", ""),
        "headers": resp_headers, "body": _truncate(body_text),
        "body_json": _try_json(body_text), "elapsed_ms": elapsed_ms,
        "backend": "wget", "saved_to": output,
    }


# ── Python urllib backend ─────────────────────────────────────────────────────

def _python(url: str, method: str, headers: dict, body: str | None,
            timeout: int, follow: bool, insecure: bool, output: str | None) -> dict:
    import ssl
    data = body.encode() if body else None
    hdrs = dict(headers)
    if data and "Content-Type" not in hdrs:
        hdrs["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    if not follow:
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
    else:
        opener = urllib.request.build_opener()

    t0 = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw_bytes = resp.read()
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            body_text = raw_bytes.decode("utf-8", errors="replace")
            status = resp.status
            resp_headers = dict(resp.headers)
            content_type = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw_bytes = e.read()
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        body_text = raw_bytes.decode("utf-8", errors="replace")
        status = e.code
        resp_headers = dict(e.headers)
        content_type = e.headers.get("Content-Type", "")
    except Exception as e:
        return {"error": str(e)}

    if output:
        Path(output).write_bytes(raw_bytes)

    return {
        "status": status, "content_type": content_type,
        "headers": resp_headers, "body": _truncate(body_text),
        "body_json": _try_json(body_text), "elapsed_ms": elapsed_ms,
        "backend": "python", "saved_to": output,
    }


# ── Dispatcher ────────────────────────────────────────────────────────────────

def _dispatch(backend: str, url: str, method: str, headers: dict,
              body: str | None, form: str | None, timeout: int,
              follow: bool, insecure: bool, output: str | None) -> dict:
    order = ["curl", "wget", "python"] if backend == "auto" else [backend]
    for b in order:
        if b == "curl":
            if backend != "curl" and not _available("curl"):
                continue
            r = _curl(url, method, headers, body, form, timeout, follow, insecure, output)
        elif b == "wget":
            if backend != "wget" and not _available("wget"):
                continue
            r = _wget(url, method, headers, body, timeout, follow, insecure, output)
        else:
            r = _python(url, method, headers, body, timeout, follow, insecure, output)

        if r.get("error") in ("curl not found", "wget not found"):
            continue
        return r
    return {"error": "no suitable HTTP backend found (curl/wget/python)"}


# ── run() ─────────────────────────────────────────────────────────────────────

def run(
    *,
    url: str,
    method: str = "GET",
    header: list[str] | None = None,
    body: str | None = None,
    form: str | None = None,
    auth: str | None = None,
    bearer: str | None = None,
    timeout: int = 30,
    follow: bool = True,
    insecure: bool = False,
    output: str | None = None,
    backend: str = "auto",
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        method = method.upper()
        valid = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        if method not in valid:
            return ForgeResult.failure(
                TOOL, [f"Invalid method '{method}'"], t.elapsed_ms,
                suggestion=f"Valid: {', '.join(sorted(valid))}",
            )

        headers = _parse_headers(header or [])
        headers.update(_auth_header(auth, bearer))

        result = _dispatch(backend, url, method, headers, body, form,
                           timeout, follow, insecure, output)

        if "error" in result and not result.get("status"):
            return ForgeResult.failure(
                TOOL, [result["error"]], t.elapsed_ms,
                suggestion="Check URL and network. curl/wget/python must be reachable.",
            )

        status = result.get("status", 0)
        data = {
            "url":          url,
            "method":       method,
            "backend":      result.get("backend", backend),
            "status":       status,
            "ok":           200 <= status < 400,
            "content_type": result.get("content_type", ""),
            "headers":      result.get("headers", {}),
            "body":         result.get("body", ""),
            "body_json":    result.get("body_json"),
            "elapsed_ms":   result.get("elapsed_ms", t.elapsed_ms),
            "saved_to":     result.get("saved_to"),
        }

        if status and not (200 <= status < 400):
            return ForgeResult(
                ok=False, tool=TOOL, data=data,
                errors=[f"HTTP {status}"], duration_ms=t.elapsed_ms,
            )

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--url",       "-u", required=True)
    p.add_argument("--method",    "-X", default="GET",
                   help="GET POST PUT PATCH DELETE HEAD OPTIONS (default: GET)")
    p.add_argument("--header",    "-H", action="append", metavar="'Key: Value'",
                   help="Header (repeatable): -H 'Accept: application/json'")
    p.add_argument("--body",      "-d", default=None, help="Request body string")
    p.add_argument("--form",      "-F", default=None, help="Form field key=value")
    p.add_argument("--auth",      default=None, metavar="user:pass")
    p.add_argument("--bearer",    default=None, metavar="TOKEN")
    p.add_argument("--timeout",   type=int, default=30)
    p.add_argument("--no-follow", action="store_false", dest="follow",
                   help="Do not follow redirects")
    p.add_argument("--insecure",  "-k", action="store_true")
    p.add_argument("--output",    "-o", default=None, metavar="FILE")
    p.add_argument("--backend",   default="auto",
                   choices=["auto", "curl", "wget", "python"],
                   help="auto → curl > wget > python")
    p.add_argument("--cwd",       default=None)


if __name__ == "__main__":
    make_cli(TOOL, "HTTP client — curl / wget / Python urllib", run, _add_args)
