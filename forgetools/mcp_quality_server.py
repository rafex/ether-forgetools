"""Domain MCP server for quality gates, tests, linting, and security."""
from __future__ import annotations

from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources
from forgetools.mcp_domain_server import build_domain_server

server = build_domain_server("forgetools-quality", ("lint", "test", "security", "secrets"))
register_domain_resources(server, "quality")
register_domain_prompts(server, "quality")


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
