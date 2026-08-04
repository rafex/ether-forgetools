"""Domain MCP server for build toolchains and construction standards."""
from __future__ import annotations

from forgetools.mcp_domain_server import build_domain_server
from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources

server = build_domain_server("forgetools-build", ("go", "npm", "cargo", "make"))
register_domain_resources(server, "build")
register_domain_prompts(server, "build")


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
