"""Domain MCP server for container and orchestration workflows."""
from __future__ import annotations

from forgetools.mcp_domain_server import build_domain_server
from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources

server = build_domain_server("forgetools-containers", ("docker", "k8s", "helm"))
register_domain_resources(server, "containers")
register_domain_prompts(server, "containers")


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
