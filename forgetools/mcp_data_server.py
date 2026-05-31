"""Domain MCP server for database inspection and migrations."""
from __future__ import annotations

from forgetools.mcp_domain_server import build_domain_server
from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources

server = build_domain_server("forgetools-data", ("db",))
register_domain_resources(server, "data")
register_domain_prompts(server, "data")


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
