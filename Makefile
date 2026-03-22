.PHONY: install install-mcp serve dev docker-build docker-run docker-serve help

PYTHON     ?= python3.13
VENV       := .venv
BIN        := $(VENV)/bin
IMAGE      ?= forgetools-mcp
DOCKERFILE := container/Dockerfile

help:
	@echo "forgetools — available targets:"
	@echo ""
	@echo "  Local"
	@echo "  make install       install forgetools (core)"
	@echo "  make install-mcp   install forgetools + fastmcp"
	@echo "  make serve         start MCP server locally (stdio)"
	@echo "  make dev           install-mcp + serve"
	@echo ""
	@echo "  Container"
	@echo "  make docker-build  build Docker image ($(IMAGE))"
	@echo "  make docker-run    run MCP server inside container (stdio)"
	@echo "  make docker-serve  build + run in one step"

# ── Local ──────────────────────────────────────────────────────────────────────

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -e .

install-mcp:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -e ".[mcp]"

serve: $(VENV)
	$(BIN)/forge-mcp

dev: install-mcp serve

$(VENV):
	$(MAKE) install-mcp

# ── Container ──────────────────────────────────────────────────────────────────

docker-build:
	docker build -f $(DOCKERFILE) -t $(IMAGE) .

docker-run:
	docker run --rm -i $(IMAGE)

docker-serve: docker-build docker-run
