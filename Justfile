# ─────────────────────────────────────────────────────────────────────────────
# Justfile — Task Runner
#
# Reglas:
# - make: solo build/compilation (estático)
# - just: task runner (ejecución, desarrollo, utilidades)
# - just puede llamar a make, pero make no puede llamar a just
# ─────────────────────────────────────────────────────────────────────────────

# Configuración
VENV := ".venv"
BIN  := VENV + "/bin"
PYTHON := "python3.13"
IMAGE := "forgetools-mcp"
DOCKERFILE := "container/Dockerfile"
MCP := "forge-mcp-file"

# ─────────────────────────────────────────────────────────────────────────────
# 🏠 Local Development
# ─────────────────────────────────────────────────────────────────────────────

# Instalar dependencias de desarrollo (usa make para el build)
install-deps:
    @make install

# Instalar dependencias + MCP (usa make para el build)
install-mcp:
    @make install-mcp

# Arrancar servidor MCP localmente (stdio)
serve mcp=MCP: install-mcp
    {{ BIN }}/{{ mcp }}

# Instalar + arrancar (modo desarrollo)
dev mcp=MCP: install-mcp
    {{ BIN }}/{{ mcp }}

# Limpiar entorno virtual
clean-venv:
    rm -rf {{ VENV }}

# ─────────────────────────────────────────────────────────────────────────────
# 🐳 Container
# ─────────────────────────────────────────────────────────────────────────────

# Construir imagen Docker
docker-build:
    docker build -f {{ DOCKERFILE }} -t {{ IMAGE }} .

# Ejecutar servidor dentro del container (stdio)
docker-run:
    docker run --rm -i {{ IMAGE }}

# Build + run en un solo paso
docker-serve: docker-build docker-run

# ─────────────────────────────────────────────────────────────────────────────
# 📚 Documentación
# ─────────────────────────────────────────────────────────────────────────────

# Regenerar OpenAPI desde el servidor en vivo
openapi: install-mcp
    {{ BIN }}/python3.13 scripts/gen_openapi.py

# Regenerar capabilities, snapshots y docs derivadas de MCP
mcp-metadata: install-mcp
    {{ BIN }}/python3.13 scripts/gen_mcp_metadata.py

# Listar MCP instalados y rutas absolutas para configurar clientes
mcp-list:
    {{ BIN }}/python3.13 scripts/list_installed_mcps.py

# Listar MCP instalados en JSON
mcp-list-json:
    {{ BIN }}/python3.13 scripts/list_installed_mcps.py --json

# ─────────────────────────────────────────────────────────────────────────────
# 🔧 Utilidades
# ─────────────────────────────────────────────────────────────────────────────

# Mostrar help de just
help:
    @just --list

# Test rápido (si aplica)
test:
    {{ BIN }}/python3.13 -m pytest

# Validar contrato vivo de todos los MCP por dominio
test-mcps:
    {{ BIN }}/python3.13 -m pytest tests/test_mcp_servers.py tests/test_mcp_metadata.py

# Verificar formato (si aplica)
lint:
    {{ BIN }}/python3.13 -m ruff check forgetools/
