"""forge-mcp — FastMCP server that exposes all forgetools as MCP tools.

Each entry in REGISTRY becomes a tool with the key name (spaces → underscores).
The existing run() functions drive execution; ForgeResult is returned as a dict.

Usage:
    forge-mcp                 # stdio transport (default, for opencode)
    python -m forgetools.mcp_server
"""
from __future__ import annotations

import functools
import importlib
import inspect

from fastmcp import FastMCP

from forgetools._forge_cli import REGISTRY

server = FastMCP("forgetools")


def _wrap(fn):
    """Wrap a run() function so it returns dict instead of ForgeResult,
    while preserving the original signature for FastMCP schema generation."""

    @functools.wraps(fn)
    def wrapped(**kwargs):
        result = fn(**kwargs)
        return result.to_dict()

    wrapped.__signature__ = inspect.signature(fn)
    return wrapped


for _key, _module_path in REGISTRY.items():
    _mod = importlib.import_module(_module_path)
    _run = getattr(_mod, "run")
    _tool_name = _key.replace(" ", "_").replace("-", "_")
    server.tool(name=_tool_name)(_wrap(_run))


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
