"""Domain MCP server for linux host ops (process, net, diagnostics)."""
from __future__ import annotations

from forgetools.mcp_domain_server import build_domain_server

server = build_domain_server("forgetools-linux", ("process", "diag", "net", "shell", "secrets"))


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
