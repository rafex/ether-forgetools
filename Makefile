# ─────────────────────────────────────────────────────────────────────────────
# Makefile — Build System
#
# Responsabilidad: Solo gestionar la construcción y configuración estática.
# Task Runner: Usa Justfile (just)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help install install-core install-mcp install-mcp-all install-mcp-file install-mcp-git install-mcp-docs install-mcp-specnative install-mcp-linux install-mcp-java install-mcp-websearch install-mcp-containers install-mcp-build install-mcp-data install-mcp-quality install-mcp-office install-mcp-python install-mcp-frontend install-mcp-observability install-mcp-cloud install-mcp-podman install-mcp-ai install-mcp-release install-mcp-deps clean clean-apple-double

UV         ?= uv
PYTHON     ?= python3.13
VENV       := .venv
BIN        := $(VENV)/bin
export COPYFILE_DISABLE := 1

help:
	@echo "forgetools — build system (Makefile)"
	@echo ""
	@echo "  Build / Setup"
	@echo "  make install       crear entorno virtual (uv) e instalar dependencias"
	@echo "  make install-core  instalar paquete base + extras MCP"
	@echo "  make install-mcp   instalar todos los MCP por dominio"
	@echo "  make install-mcp-all        instalar todos los MCP por dominio"
	@echo "  make install-mcp-file       instalar MCP dominio file"
	@echo "  make install-mcp-git        instalar MCP dominio git/github"
	@echo "  make install-mcp-docs       instalar MCP dominio docs/web/openapi"
	@echo "  make install-mcp-specnative instalar MCP dominio specnative/context"
	@echo "  make install-mcp-linux      instalar MCP dominio linux/process/net/diag"
	@echo "  make install-mcp-java       instalar MCP dominio java + resources/prompts"
	@echo "  make install-mcp-websearch  instalar MCP dominio websearch (DDGS + navegacion)"
	@echo "  make install-mcp-containers instalar MCP dominio docker/k8s/helm"
	@echo "  make install-mcp-build      instalar MCP dominio go/npm/cargo/make"
	@echo "  make install-mcp-data       instalar MCP dominio db"
	@echo "  make install-mcp-quality    instalar MCP dominio quality/lint/test/security"
	@echo "  make install-mcp-office     instalar MCP dominio office/pdf/docs"
	@echo "  make install-mcp-python     instalar MCP dominio python/uv"
	@echo "  make install-mcp-frontend   instalar MCP dominio frontend"
	@echo "  make install-mcp-observability instalar MCP dominio logs/observability"
	@echo "  make install-mcp-cloud      instalar MCP dominio cloud"
	@echo "  make install-mcp-podman     instalar MCP dominio podman/bastion"
	@echo "  make install-mcp-ai         instalar MCP dominio ai"
	@echo "  make install-mcp-release    instalar MCP dominio release"
	@echo "  make install-mcp-deps       instalar MCP dominio deps"
	@echo "  make clean         limpiar artefactos de build"
	@echo "  make clean-apple-double  eliminar archivos ._* de macOS en el venv"
	@echo ""
	@echo "  Task Runner (Justfile)"
	@echo "  just help          mostrar tareas disponibles"
	@echo "  just serve         iniciar servidor MCP"
	@echo "  just dev           modo desarrollo"

# ── Setup ──────────────────────────────────────────────────────────────────────

$(VENV):
	$(UV) venv --python $(PYTHON) $(VENV)
	$(UV) pip install --python $(BIN)/python --upgrade pip

install: $(VENV)
	$(UV) pip install --python $(BIN)/python -e .
	$(MAKE) clean-apple-double

install-core: $(VENV)
	$(UV) pip install --python $(BIN)/python -e ".[mcp]"
	$(MAKE) clean-apple-double

install-mcp: install-mcp-all

install-mcp-file: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/file
	@echo "MCP listo: forge-mcp-file"

install-mcp-git: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/git
	@echo "MCP listo: forge-mcp-git"

install-mcp-docs: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/docs
	@echo "MCP listo: forge-mcp-docs"

install-mcp-specnative: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/specnative
	@echo "MCP listo: forge-mcp-specnative"

install-mcp-linux: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/linux
	@echo "MCP listo: forge-mcp-linux"

install-mcp-java: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/java
	@echo "MCP listo: forge-mcp-java"

install-mcp-websearch: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/websearch
	@echo "MCP listo: forge-mcp-websearch"

install-mcp-containers: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/containers
	@echo "MCP listo: forge-mcp-containers"

install-mcp-build: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/build
	@echo "MCP listo: forge-mcp-build"

install-mcp-data: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/data
	@echo "MCP listo: forge-mcp-data"

install-mcp-quality: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/quality
	@echo "MCP listo: forge-mcp-quality"

install-mcp-office: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/office
	@echo "MCP listo: forge-mcp-office"

install-mcp-python: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/python
	@echo "MCP listo: forge-mcp-python"

install-mcp-frontend: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/frontend
	@echo "MCP listo: forge-mcp-frontend"

install-mcp-observability: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/observability
	@echo "MCP listo: forge-mcp-observability"

install-mcp-cloud: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/cloud
	@echo "MCP listo: forge-mcp-cloud"

install-mcp-podman: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/podman
	@echo "MCP listo: forge-mcp-podman"

install-mcp-ai: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/ai
	@echo "MCP listo: forge-mcp-ai"

install-mcp-release: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/release
	@echo "MCP listo: forge-mcp-release"

install-mcp-deps: install-core
	$(UV) pip install --python $(BIN)/python --no-deps -e ./mcps/deps
	@echo "MCP listo: forge-mcp-deps"

install-mcp-all: install-mcp-file install-mcp-git install-mcp-docs install-mcp-specnative install-mcp-linux install-mcp-java install-mcp-websearch install-mcp-containers install-mcp-build install-mcp-data install-mcp-quality install-mcp-office install-mcp-python install-mcp-frontend install-mcp-observability install-mcp-cloud install-mcp-podman install-mcp-ai install-mcp-release install-mcp-deps
	@echo "MCPs de dominio listos: file git docs specnative linux java websearch containers build data quality office python frontend observability cloud podman ai release deps"

clean:
	rm -rf $(VENV) __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

clean-apple-double:
	find $(VENV)/lib -name "._*" -delete 2>/dev/null || true
