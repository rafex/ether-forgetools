"""Domain MCP server for file/content operations."""
from __future__ import annotations

from forgetools.mcp_domain_server import build_domain_server

server = build_domain_server(
    "forgetools-file",
    ("fs", "search", "edit", "diff", "text", "template", "json", "config"),
)


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
