"""Domain MCP server for release workflows."""
from __future__ import annotations

from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources
from forgetools.mcp_domain_server import build_domain_server

server = build_domain_server("forgetools-release", ("release", "gh", "docs"))
register_domain_resources(server, "release")
register_domain_prompts(server, "release")


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
