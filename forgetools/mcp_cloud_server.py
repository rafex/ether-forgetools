"""Domain MCP server for cloud provider context."""
from __future__ import annotations

from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources
from forgetools.mcp_domain_server import build_domain_server

server = build_domain_server("forgetools-cloud", ("cloud",))
register_domain_resources(server, "cloud")
register_domain_prompts(server, "cloud")


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
