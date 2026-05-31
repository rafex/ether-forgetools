"""Domain MCP server for file/content operations."""
from __future__ import annotations

from forgetools.mcp_domain_server import build_domain_server
from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources

server = build_domain_server(
    "forgetools-file",
    ("fs", "search", "edit", "diff", "text", "template", "json", "config"),
)
register_domain_resources(server, "file")
register_domain_prompts(server, "file")


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
