"""Domain MCP server for web search and web navigation."""
from __future__ import annotations

from forgetools.mcp_domain_server import build_domain_server

server = build_domain_server("forgetools-websearch", ("websearch", "web"))


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
