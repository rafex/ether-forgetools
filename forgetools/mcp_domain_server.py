"""Shared helpers to build domain-scoped MCP servers."""
from __future__ import annotations

import functools
import importlib
import inspect
import json
from typing import Iterable

from fastmcp import FastMCP

from forgetools._forge_cli import REGISTRY


def _wrap(fn):
    """Return dict instead of ForgeResult, preserve signature for schema gen."""
    @functools.wraps(fn)
    def wrapped(**kwargs):
        result = fn(**kwargs)
        return result.to_dict()
    wrapped.__signature__ = inspect.signature(fn)
    return wrapped


def _tool_description(key: str, module_path: str) -> str:
    """Build a stable MCP description for a forgetools tool."""
    try:
        mod = importlib.import_module(module_path)
    except Exception:
        mod = None

    if mod is not None:
        run_doc = inspect.getdoc(getattr(mod, "run", None)) or ""
        if run_doc:
            return run_doc.splitlines()[0].strip()

        module_doc = inspect.getdoc(mod) or ""
        if module_doc:
            first_line = module_doc.splitlines()[0].strip()
            if "-" in first_line:
                _, _, first_line = first_line.partition("-")
                first_line = first_line.strip()
            if first_line:
                return first_line.rstrip(".")

    words = key.replace("-", " ").split()
    if not words:
        return "Run a forgetools command"

    category = words[0]
    action = " ".join(words[1:]) or "command"
    return f"Run the {category} {action} forgetools command"


def _domain_registry(categories: Iterable[str]) -> dict[str, str]:
    allowed = set(categories)
    return {k: v for k, v in REGISTRY.items() if k.split(" ", 1)[0] in allowed}


def build_domain_server(name: str, categories: Iterable[str]) -> FastMCP:
    """Create a FastMCP server that only exposes tools for given categories."""
    server = FastMCP(name)
    category_list = tuple(categories)
    domain_registry = _domain_registry(category_list)

    for key, module_path in domain_registry.items():
        mod = importlib.import_module(module_path)
        run = getattr(mod, "run")
        tool_name = key.replace(" ", "_").replace("-", "_")
        description = _tool_description(key, module_path)
        wrapped = _wrap(run)
        wrapped.__doc__ = description
        server.tool(name=tool_name, description=description)(wrapped)

    @server.resource("forge://catalog")
    def resource_catalog() -> str:
        """List tools available in this domain server."""
        lines = [
            f"# {name} Catalog",
            f"Total tools: {len(domain_registry)}",
        ]
        current_cat = None
        for key, module_path in domain_registry.items():
            category = key.split(" ", 1)[0]
            if category != current_cat:
                lines.append(f"\n## {category.upper()}")
                current_cat = category
            tool_name = key.replace(" ", "_").replace("-", "_")
            lines.append(f"\n### `{tool_name}`")
            lines.append(f"- forge key: `forge {key}`")
            lines.append(f"- description: {_tool_description(key, module_path)}")
        return "\n".join(lines)

    @server.resource("forge://capabilities")
    def resource_capabilities() -> str:
        """Machine-readable capabilities manifest for this domain server."""
        tools = [
            {
                "name": key.replace(" ", "_").replace("-", "_"),
                "forge_key": f"forge {key}",
                "category": key.split(" ", 1)[0],
                "description": _tool_description(key, module_path),
            }
            for key, module_path in domain_registry.items()
        ]
        return json.dumps(
            {
                "name": name,
                "version": "0.1.0",
                "categories": list(category_list),
                "tools": tools,
                "resources": ["forge://catalog", "forge://capabilities"],
            },
            indent=2,
        )

    return server
