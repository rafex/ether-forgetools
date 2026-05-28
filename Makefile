# ─────────────────────────────────────────────────────────────────────────────
# Makefile — Build System
#
# Responsabilidad: Solo gestionar la construcción y configuración estática.
# Task Runner: Usa Justfile (just)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help install install-mcp install-mcp-all install-mcp-file install-mcp-git install-mcp-docs install-mcp-specnative install-mcp-linux install-mcp-java install-mcp-websearch clean clean-apple-double

PYTHON     ?= python3.13
VENV       := .venv
BIN        := $(VENV)/bin
export COPYFILE_DISABLE := 1

help:
	@echo "forgetools — build system (Makefile)"
	@echo ""
	@echo "  Build / Setup"
	@echo "  make install       crear entorno virtual e instalar dependencias"
	@echo "  make install-mcp   instalar dependencias + extras mcp"
	@echo "  make install-mcp-all        instalar MCP monolitico + todos los MCP por dominio"
	@echo "  make install-mcp-file       instalar MCP dominio file"
	@echo "  make install-mcp-git        instalar MCP dominio git/github"
	@echo "  make install-mcp-docs       instalar MCP dominio docs/web/openapi"
	@echo "  make install-mcp-specnative instalar MCP dominio specnative/context"
	@echo "  make install-mcp-linux      instalar MCP dominio linux/process/net/diag"
	@echo "  make install-mcp-java       instalar MCP dominio java + resources/prompts"
	@echo "  make install-mcp-websearch  instalar MCP dominio websearch (DDGS + navegacion)"
	@echo "  make clean         limpiar artefactos de build"
	@echo "  make clean-apple-double  eliminar archivos ._* de macOS en el venv"
	@echo ""
	@echo "  Task Runner (Justfile)"
	@echo "  just help          mostrar tareas disponibles"
	@echo "  just serve         iniciar servidor MCP"
	@echo "  just dev           modo desarrollo"

# ── Setup ──────────────────────────────────────────────────────────────────────

$(VENV):
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip

install: $(VENV)
	$(BIN)/pip install -e .
	$(MAKE) clean-apple-double

install-mcp: $(VENV)
	$(BIN)/pip install -e ".[mcp]"
	$(MAKE) clean-apple-double

install-mcp-file: install-mcp
	@echo "MCP listo: forge-mcp-file"

install-mcp-git: install-mcp
	@echo "MCP listo: forge-mcp-git"

install-mcp-docs: install-mcp
	@echo "MCP listo: forge-mcp-docs"

install-mcp-specnative: install-mcp
	@echo "MCP listo: forge-mcp-specnative"

install-mcp-linux: install-mcp
	@echo "MCP listo: forge-mcp-linux"

install-mcp-java: install-mcp
	@echo "MCP listo: forge-mcp-java"

install-mcp-websearch: install-mcp
	@echo "MCP listo: forge-mcp-websearch"

install-mcp-all: install-mcp-file install-mcp-git install-mcp-docs install-mcp-specnative install-mcp-linux install-mcp-java install-mcp-websearch
	@echo "MCPs de dominio listos: file git docs specnative linux java websearch"

clean:
	rm -rf $(VENV) __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

clean-apple-double:
	find $(VENV)/lib -name "._*" -delete 2>/dev/null || true
