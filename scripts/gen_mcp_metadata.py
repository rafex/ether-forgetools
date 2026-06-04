"""Generate domain MCP capabilities, snapshots, and derived documentation."""
from __future__ import annotations

import ast
import json
import os
import selectors
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
VENV_BIN = ROOT / ".venv" / "bin"
TIMEOUT_SECONDS = 10


def _server_categories(server_path: Path) -> tuple[str, str, list[str]]:
    tree = ast.parse(server_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "id", None) != "build_domain_server":
            continue
        if len(node.args) < 2:
            break
        name_node = node.args[0]
        categories_node = node.args[1]
        name = name_node.value if isinstance(name_node, ast.Constant) else server_path.stem
        categories = []
        if isinstance(categories_node, (ast.Tuple, ast.List)):
            categories = [
                elt.value
                for elt in categories_node.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
        domain = server_path.stem.removeprefix("mcp_").removesuffix("_server")
        return domain, str(name), categories
    raise ValueError(f"Cannot find build_domain_server call in {server_path}")


def _domain_servers() -> dict[str, dict[str, Any]]:
    servers: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "forgetools").glob("mcp_*_server.py")):
        if path.name in {"mcp_domain_server.py", "mcp_domain_extras.py", "mcp_prompts.py"}:
            continue
        domain, server_name, categories = _server_categories(path)
        pyproject_path = ROOT / "mcps" / domain / "pyproject.toml"
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        servers[domain] = {
            "domain": domain,
            "binary": f"forge-mcp-{domain}",
            "server_name": server_name,
            "version": pyproject["project"]["version"],
            "categories": categories,
            "server_module": f"forgetools.{path.stem}",
            "server_file": str(path.relative_to(ROOT)),
            "pyproject": f"mcps/{domain}/pyproject.toml",
        }
    return servers


def _send(proc: subprocess.Popen[str], msg: dict[str, Any]) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def _recv(proc: subprocess.Popen[str], *, timeout: int = TIMEOUT_SECONDS) -> dict[str, Any]:
    assert proc.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    try:
        if not selector.select(timeout):
            raise TimeoutError(f"MCP server did not respond within {timeout}s")
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed stdout")
        return json.loads(line)
    finally:
        selector.close()


def _request(binary: str, method: str) -> dict[str, Any]:
    binary_path = VENV_BIN / binary
    command = [str(binary_path)] if binary_path.exists() else [binary]
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=ROOT,
    )
    try:
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "gen_mcp_metadata", "version": "1.0"},
                },
            },
        )
        _recv(proc)
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": method, "params": {}})
        response = _recv(proc)
        if "error" in response:
            raise RuntimeError(f"{binary} {method} failed: {response['error']}")
        return response["result"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


def _minimal_tool(tool: dict[str, Any]) -> dict[str, Any]:
    schema = tool.get("inputSchema") or {}
    return {
        "name": tool["name"],
        "description": tool.get("description", ""),
        "required": schema.get("required", []),
        "properties": sorted((schema.get("properties") or {}).keys()),
    }


def _minimal_resource(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": resource.get("name", ""),
        "uri": resource.get("uri", ""),
        "description": resource.get("description", ""),
    }


def _minimal_prompt(prompt: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": prompt.get("name", ""),
        "description": prompt.get("description", ""),
        "arguments": [
            {
                "name": arg.get("name", ""),
                "required": bool(arg.get("required", False)),
            }
            for arg in prompt.get("arguments", [])
        ],
    }


def _domain_capabilities(domain_info: dict[str, Any]) -> dict[str, Any]:
    binary = domain_info["binary"]
    tools = sorted((_minimal_tool(t) for t in _request(binary, "tools/list").get("tools", [])), key=lambda t: t["name"])
    resources = sorted(
        (_minimal_resource(r) for r in _request(binary, "resources/list").get("resources", [])),
        key=lambda r: r["uri"],
    )
    prompts = sorted(
        (_minimal_prompt(p) for p in _request(binary, "prompts/list").get("prompts", [])),
        key=lambda p: p["name"],
    )
    return {
        "schema_version": "1.0",
        **domain_info,
        "tools": tools,
        "resources": resources,
        "prompts": prompts,
        "counts": {
            "tools": len(tools),
            "resources": len(resources),
            "prompts": len(prompts),
        },
    }


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_docs(capabilities: list[dict[str, Any]]) -> None:
    lines = [
        "# MCP Capabilities",
        "",
        "Documento generado por `scripts/gen_mcp_metadata.py`.",
        "",
        "| MCP | Categorias | Tools | Resources | Prompts | Capabilities |",
        "|---|---|---:|---:|---:|---|",
    ]
    for cap in capabilities:
        lines.append(
            "| `{binary}` | `{categories}` | {tools} | {resources} | {prompts} | `{path}` |".format(
                binary=cap["binary"],
                categories="`, `".join(cap["categories"]),
                tools=cap["counts"]["tools"],
                resources=cap["counts"]["resources"],
                prompts=cap["counts"]["prompts"],
                path=f"mcps/{cap['domain']}/capabilities.json",
            )
        )
    lines.extend(["", "## Detalle por Dominio", ""])
    for cap in capabilities:
        lines.extend(
            [
                f"### `{cap['binary']}`",
                "",
                f"- Server: `{cap['server_name']}`",
                f"- Categorias: `{ '`, `'.join(cap['categories']) }`",
                f"- Tools: {cap['counts']['tools']}",
                f"- Resources: {cap['counts']['resources']}",
                f"- Prompts: {cap['counts']['prompts']}",
                "",
                "Tools:",
                "",
            ]
        )
        for tool in cap["tools"]:
            lines.append(f"- `{tool['name']}`: {tool['description']}")
        if cap["resources"]:
            lines.extend(["", "Resources:", ""])
            for resource in cap["resources"]:
                lines.append(f"- `{resource['uri']}`: {resource['description']}")
        if cap["prompts"]:
            lines.extend(["", "Prompts:", ""])
            for prompt in cap["prompts"]:
                lines.append(f"- `{prompt['name']}`: {prompt['description'].splitlines()[0]}")
        lines.append("")
    output = ROOT / "docs" / "generated" / "mcp-capabilities.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    domains = _domain_servers()
    capabilities = []
    for domain in sorted(domains):
        cap = _domain_capabilities(domains[domain])
        capabilities.append(cap)
        _write_json(ROOT / "mcps" / domain / "capabilities.json", cap)
        _write_json(
            ROOT / "snapshots" / "mcp" / f"{domain}.json",
            {
                "schema_version": cap["schema_version"],
                "domain": domain,
                "binary": cap["binary"],
                "tools": cap["tools"],
                "resources": cap["resources"],
                "prompts": cap["prompts"],
                "counts": cap["counts"],
            },
        )
    _write_docs(capabilities)
    print(f"Generated MCP metadata for {len(capabilities)} domains")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
