"""Generate openapi/forgetools.json from the live domain MCP servers."""
from __future__ import annotations

import json
import os
import subprocess

DOMAIN_MCP_BINARIES = [
    "forge-mcp-file",
    "forge-mcp-git",
    "forge-mcp-docs",
    "forge-mcp-specnative",
    "forge-mcp-linux",
    "forge-mcp-java",
    "forge-mcp-websearch",
    "forge-mcp-containers",
    "forge-mcp-build",
    "forge-mcp-data",
    "forge-mcp-quality",
    "forge-mcp-office",
    "forge-mcp-python",
    "forge-mcp-frontend",
    "forge-mcp-observability",
    "forge-mcp-cloud",
    "forge-mcp-podman",
    "forge-mcp-ai",
    "forge-mcp-release",
    "forge-mcp-deps",
]


def get_tools(command: str) -> list[dict]:
    venv_bin = os.path.join(os.path.dirname(__file__), "..", ".venv", "bin")
    server_bin = os.path.join(venv_bin, command)

    proc = subprocess.Popen(
        [server_bin],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    def send(msg: dict) -> None:
        proc.stdin.write((json.dumps(msg) + "\n").encode())
        proc.stdin.flush()

    def recv() -> dict:
        return json.loads(proc.stdout.readline())

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "gen_openapi", "version": "1.0"},
    }})
    recv()

    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    resp = recv()
    proc.terminate()

    return resp["result"]["tools"]


def get_domain_tools() -> list[dict]:
    tools_by_name: dict[str, dict] = {}

    for command in DOMAIN_MCP_BINARIES:
        for tool in get_tools(command):
            tools_by_name.setdefault(tool["name"], tool)

    return list(tools_by_name.values())


def build_spec(tools: list[dict]) -> dict:
    paths: dict = {}

    for t in tools:
        name = t["name"]
        description = t.get("description") or f"Run {name.replace('_', ' ')}"
        input_schema = {k: v for k, v in t.get("inputSchema", {}).items()
                        if k != "additionalProperties"}
        output_schema = t.get("outputSchema") or {"$ref": "#/components/schemas/ForgeResult"}

        paths[f"/tools/{name}"] = {
            "post": {
                "operationId": name,
                "summary": description,
                "tags": [name.split("_")[0]],
                "requestBody": {
                    "required": False,
                    "content": {"application/json": {"schema": input_schema}},
                },
                "responses": {
                    "200": {
                        "description": "ForgeResult",
                        "content": {"application/json": {"schema": output_schema}},
                    }
                },
            }
        }

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "forgetools domain MCPs",
            "version": "0.1.0",
            "description": (
                "Structured Python toolkit for code agents. "
                "Every tool returns a ForgeResult JSON object with "
                "ok, tool, data, errors, duration_ms."
            ),
        },
        "paths": paths,
        "components": {
            "schemas": {
                "ForgeResult": {
                    "type": "object",
                    "required": ["ok", "tool"],
                    "properties": {
                        "ok":          {"type": "boolean"},
                        "tool":        {"type": "string"},
                        "data":        {"description": "Structured output, shape varies per tool"},
                        "errors":      {"type": "array", "items": {"type": "string"}},
                        "duration_ms": {"type": "integer"},
                        "suggestion":  {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    },
                }
            }
        },
    }


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(root, "openapi", "forgetools.json")

    tools = get_domain_tools()
    spec = build_spec(tools)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(spec, f, indent=2)
        f.write("\n")

    print(f"Generated {len(tools)} tools → {out_path}")


if __name__ == "__main__":
    main()
