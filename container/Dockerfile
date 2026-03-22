FROM python:3.11-slim

WORKDIR /app

# System tools used by forgetools at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY forgetools/ forgetools/

# Install forgetools + MCP deps
RUN pip install --no-cache-dir -e ".[mcp]"

# MCP servers communicate over stdio — no port needed
ENTRYPOINT ["forge-mcp"]
