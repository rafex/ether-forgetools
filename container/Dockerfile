FROM python:3.11-alpine

WORKDIR /app

# System tools used by forgetools at runtime
RUN apk add --no-cache git curl

# Copy project files
COPY pyproject.toml .
COPY forgetools/ forgetools/

# Install forgetools + MCP deps
RUN pip install --no-cache-dir -e ".[mcp]"

# MCP servers communicate over stdio — no port needed
ENTRYPOINT ["forge-mcp"]
