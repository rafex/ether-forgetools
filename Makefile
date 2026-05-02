# ─────────────────────────────────────────────────────────────────────────────
# Makefile — Build System
#
# Responsabilidad: Solo gestionar la construcción y configuración estática.
# Task Runner: Usa Justfile (just)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help install install-mcp clean clean-apple-double

PYTHON     ?= python3.13
VENV       := .venv
BIN        := $(VENV)/bin

help:
	@echo "forgetools — build system (Makefile)"
	@echo ""
	@echo "  Build / Setup"
	@echo "  make install       crear entorno virtual e instalar dependencias"
	@echo "  make install-mcp   instalar dependencias + extras mcp"
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

clean:
	rm -rf $(VENV) __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

clean-apple-double:
	find $(VENV)/lib -name "._*.dist-info" -delete 2>/dev/null || true
	find $(VENV)/lib -name "._*.pth"       -delete 2>/dev/null || true
