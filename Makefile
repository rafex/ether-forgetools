.PHONY: install install-mcp serve dev help

PYTHON  ?= python3
VENV    := .venv
BIN     := $(VENV)/bin

help:
	@echo "forgetools — available targets:"
	@echo "  make install      install forgetools (core)"
	@echo "  make install-mcp  install forgetools + fastmcp"
	@echo "  make serve        start MCP server (stdio)"
	@echo "  make dev          install + start MCP server"

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
