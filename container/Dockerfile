FROM python:3.11-alpine

WORKDIR /app

# System tools used by forgetools at runtime
RUN apk add --no-cache git curl

# Copy project files
COPY pyproject.toml .
COPY forgetools/ forgetools/
COPY mcps/ mcps/

# Install forgetools + all domain MCP entrypoints
RUN pip install --no-cache-dir -e ".[mcp]" \
    && for domain in mcps/*; do pip install --no-cache-dir --no-deps -e "$domain"; done

# MCP servers communicate over stdio - no port needed
ENTRYPOINT ["forge-mcp-file"]
