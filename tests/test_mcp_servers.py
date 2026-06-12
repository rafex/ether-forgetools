from __future__ import annotations

import json
import os
import selectors
import subprocess
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parent.parent
VENV_BIN = ROOT / ".venv" / "bin"
DOMAINS = sorted(path.parent.name for path in (ROOT / "mcps").glob("*/pyproject.toml"))
REQUEST_TIMEOUT_SECONDS = 15


class MCPClient:
    def __init__(self, binary: Path) -> None:
        self.binary = binary
        self.proc: subprocess.Popen[str] | None = None
        self._next_id = 1

    def __enter__(self) -> "MCPClient":
        self.proc = subprocess.Popen(
            [str(self.binary)],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        return self

    def __exit__(self, *_: object) -> None:
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=2)

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        response = self._receive(request_id)
        assert "error" not in response, (
            f"{self.binary.name} {method} returned RPC error: {response.get('error')}"
        )
        return response.get("result", {})

    def initialize(self) -> dict[str, Any]:
        result = self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "forgetools-tests", "version": "1.0"},
            },
        )
        self.notify("notifications/initialized")
        return result

    def _send(self, message: dict[str, Any]) -> None:
        assert self.proc is not None and self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def _receive(self, request_id: int) -> dict[str, Any]:
        assert self.proc is not None and self.proc.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(self.proc.stdout, selectors.EVENT_READ)
        try:
            while True:
                if not selector.select(REQUEST_TIMEOUT_SECONDS):
                    raise AssertionError(
                        f"{self.binary.name} did not answer request {request_id}. "
                        f"stderr: {self._stderr()}"
                    )
                line = self.proc.stdout.readline()
                if not line:
                    raise AssertionError(
                        f"{self.binary.name} closed stdout. stderr: {self._stderr()}"
                    )
                response = json.loads(line)
                if response.get("id") == request_id:
                    return response
        finally:
            selector.close()

    def _stderr(self) -> str:
        if self.proc is None or self.proc.stderr is None or self.proc.poll() is None:
            return ""
        return self.proc.stderr.read().strip()


def _load_capabilities(domain: str) -> dict[str, Any]:
    path = ROOT / "mcps" / domain / "capabilities.json"
    return json.loads(path.read_text(encoding="utf-8"))


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
                "name": argument.get("name", ""),
                "required": bool(argument.get("required", False)),
            }
            for argument in prompt.get("arguments", [])
        ],
    }


def _prompt_value(name: str) -> str:
    values = {
        "api_name": "example-api",
        "app": "example-app",
        "base_dir": ".",
        "category": "fs",
        "commits": "abc123",
        "container_name": "example-container",
        "description": "Contract test description",
        "goals": "Deliver an observable result",
        "hotfix": "critical-fix",
        "image": "example/app:latest",
        "initiative": "contract-test",
        "migration_name": "add_example_table",
        "name": "Example Project",
        "next_steps": "Run validation and review the result",
        "package_base": "com.example",
        "pr_number": "1",
        "problem": "A concrete problem needs a documented solution",
        "query": "example dependency",
        "report_name": "Example Report",
        "run_id": "1",
        "scope": ".",
        "service_name": "example-service",
        "stack": "api,ui",
        "summary": "Contract test handoff",
        "table_sources": "example.csv",
        "target": ".",
        "task_id": "TASK-0001",
        "tasks": "api,tests",
        "title": "Contract test pull request",
        "tool_name": "example-tool",
        "type": "feat",
        "users": "Developers and maintainers",
        "version": "v0.1.0",
    }
    return values.get(name, "contract-test")


def _assert_tool_schemas(domain: str, tools: list[dict[str, Any]]) -> None:
    names = [tool["name"] for tool in tools]
    assert len(names) == len(set(names)), f"{domain}: duplicate tool names"

    for tool in tools:
        assert tool.get("description", "").strip(), f"{domain}/{tool['name']}: missing description"
        schema = tool.get("inputSchema")
        assert isinstance(schema, dict), f"{domain}/{tool['name']}: missing inputSchema"
        assert schema.get("type") == "object", f"{domain}/{tool['name']}: inputSchema is not object"
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        assert isinstance(properties, dict), f"{domain}/{tool['name']}: invalid properties"
        assert isinstance(required, list), f"{domain}/{tool['name']}: invalid required list"
        assert set(required) <= set(properties), (
            f"{domain}/{tool['name']}: required fields absent from properties"
        )


@pytest.mark.parametrize("domain", DOMAINS)
def test_mcp_domain_contract(domain: str) -> None:
    capabilities = _load_capabilities(domain)
    binary = VENV_BIN / capabilities["binary"]
    assert binary.is_file(), f"{domain}: MCP binary is not installed: {binary}"
    assert os.access(binary, os.X_OK), f"{domain}: MCP binary is not executable: {binary}"

    with MCPClient(binary) as client:
        initialized = client.initialize()
        assert initialized["serverInfo"]["name"] == capabilities["server_name"]
        assert initialized.get("protocolVersion")
        assert client.request("ping") == {}

        tools = client.request("tools/list").get("tools", [])
        resources = client.request("resources/list").get("resources", [])
        prompts = client.request("prompts/list").get("prompts", [])
        resource_templates = client.request("resources/templates/list").get(
            "resourceTemplates", []
        )

        _assert_tool_schemas(domain, tools)

        actual_tools = sorted((_minimal_tool(tool) for tool in tools), key=lambda item: item["name"])
        actual_resources = sorted(
            (_minimal_resource(resource) for resource in resources),
            key=lambda item: item["uri"],
        )
        actual_prompts = sorted(
            (_minimal_prompt(prompt) for prompt in prompts),
            key=lambda item: item["name"],
        )

        assert actual_tools == capabilities["tools"], f"{domain}: live tools differ from manifest"
        assert actual_resources == capabilities["resources"], (
            f"{domain}: live resources differ from manifest"
        )
        assert actual_prompts == capabilities["prompts"], (
            f"{domain}: live prompts differ from manifest"
        )
        assert capabilities["counts"] == {
            "tools": len(tools),
            "resources": len(resources),
            "prompts": len(prompts),
        }

        for template in resource_templates:
            assert template.get("name"), f"{domain}: resource template missing name"
            assert template.get("uriTemplate"), f"{domain}: resource template missing URI"
            assert template.get("description"), (
                f"{domain}/{template.get('name')}: resource template missing description"
            )

        for uri in ("forge://catalog", "forge://capabilities"):
            result = client.request("resources/read", {"uri": uri})
            contents = result.get("contents", [])
            assert contents, f"{domain}: {uri} returned no content"
            assert any(item.get("text", "").strip() for item in contents), (
                f"{domain}: {uri} returned empty content"
            )

        for prompt in prompts:
            arguments = {
                argument["name"]: _prompt_value(argument["name"])
                for argument in prompt.get("arguments", [])
                if argument.get("required")
            }
            result = client.request(
                "prompts/get",
                {"name": prompt["name"], "arguments": arguments},
            )
            messages = result.get("messages", [])
            assert messages, f"{domain}/{prompt['name']}: prompt rendered no messages"
            assert all(message.get("role") in {"user", "assistant"} for message in messages)
