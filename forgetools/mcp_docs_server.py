"""Domain MCP server for docs and web extraction workflows."""
from __future__ import annotations

from forgetools.mcp_domain_server import build_domain_server

server = build_domain_server("forgetools-docs", ("docs", "openapi", "web"))


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
