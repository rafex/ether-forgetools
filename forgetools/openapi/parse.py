"""forgetools.openapi.parse — Parse OpenAPI 2/3 YAML or JSON spec files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "openapi.parse"


def run(
    *,
    path: str = "openapi.yaml",
    cwd: str | None = None,
    endpoint: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        full_path = Path(cwd or ".") / path
        if not full_path.exists():
            return ForgeResult.failure(
                TOOL,
                [f"OpenAPI file not found: {full_path}"],
                t.elapsed_ms,
                suggestion="Check that the OpenAPI spec file exists at the given path",
            )
        try:
            spec = _load_spec(full_path)
            data = _parse(spec, endpoint)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Failed to parse OpenAPI spec: {e}"], t.elapsed_ms)


def _load_spec(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    # Try yaml first (may be installed as a transitive dep)
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ImportError:
        pass
    # Fall back to JSON
    return json.loads(text)


def _parse(spec: dict, endpoint_filter: str | None) -> dict:
    # Detect version
    version = spec.get("openapi") or spec.get("swagger", "unknown")
    info = spec.get("info", {})
    title = info.get("title", "")

    # Base URL
    if spec.get("openapi", "").startswith("3"):
        servers = spec.get("servers", [])
        base_url = servers[0].get("url", "") if servers else ""
    else:
        host = spec.get("host", "")
        base_path = spec.get("basePath", "/")
        schemes = spec.get("schemes", ["https"])
        base_url = f"{schemes[0]}://{host}{base_path}" if host else base_path

    paths = spec.get("paths", {})
    endpoints: list[dict] = []

    for path_str, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        if endpoint_filter and endpoint_filter not in path_str:
            continue
        for method, operation in path_item.items():
            if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
                continue
            if not isinstance(operation, dict):
                continue

            params = [
                {
                    "name": p.get("name", ""),
                    "in": p.get("in", ""),
                    "required": p.get("required", False),
                    "description": p.get("description", ""),
                }
                for p in operation.get("parameters", [])
                if isinstance(p, dict)
            ]

            req_body = None
            if "requestBody" in operation:
                rb = operation["requestBody"]
                content = rb.get("content", {})
                req_body = {
                    "required": rb.get("required", False),
                    "content_types": list(content.keys()),
                }

            responses = {
                str(code): {
                    "description": resp.get("description", "") if isinstance(resp, dict) else ""
                }
                for code, resp in operation.get("responses", {}).items()
            }

            endpoints.append({
                "path": path_str,
                "method": method.upper(),
                "operationId": operation.get("operationId", ""),
                "summary": operation.get("summary", ""),
                "parameters": params,
                "request_body": req_body,
                "responses": responses,
            })

    return {
        "version": str(version),
        "title": title,
        "base_url": base_url,
        "endpoints": endpoints,
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default="openapi.yaml", help="Path to OpenAPI spec file")
    p.add_argument("--endpoint", default=None, help="Filter to endpoints matching this path substring")


if __name__ == "__main__":
    make_cli(TOOL, "Parse OpenAPI spec file", run, _add_args)
