"""Domain MCP server for Linux host operations and diagnostics."""
from __future__ import annotations

from forgetools.mcp_domain_server import build_domain_server
from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources

server = build_domain_server("forgetools-linux", ("process", "diag", "net", "shell", "linux"))
register_domain_resources(server, "linux")
register_domain_prompts(server, "linux")


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
