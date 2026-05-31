# MCP Usage & Installation

Guia operativa de instalacion y uso de los MCP de `forgetools`.

## Layout de empaquetado

- `pyproject.toml` (raiz): paquete base `forgetools` + CLI `forge`.
- `mcps/<dominio>/pyproject.toml`: paquete de cada MCP de dominio.

Dominios actuales con `pyproject.toml` propio:

- `mcps/file/pyproject.toml`
- `mcps/git/pyproject.toml`
- `mcps/docs/pyproject.toml`
- `mcps/specnative/pyproject.toml`
- `mcps/linux/pyproject.toml`
- `mcps/java/pyproject.toml`
- `mcps/websearch/pyproject.toml`
- `mcps/containers/pyproject.toml`
- `mcps/build/pyproject.toml`
- `mcps/data/pyproject.toml`

## 1) Instalacion

### Base

```bash
make install
```

### Todos los MCP por dominio (incluye fastmcp + ddgs, via uv)

```bash
make install-mcp
```

### Uso directo con uv (alternativa)

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e .
uv pip install --python .venv/bin/python -e ".[mcp]"
for domain in file git docs specnative linux java websearch containers build data; do
  uv pip install --python .venv/bin/python --no-deps -e "./mcps/${domain}"
done
```

### MCPs de dominio

```bash
make install-mcp-file
make install-mcp-git
make install-mcp-docs
make install-mcp-specnative
make install-mcp-linux
make install-mcp-java
make install-mcp-websearch
make install-mcp-containers
make install-mcp-build
make install-mcp-data
```

Cada comando `install-mcp-<dominio>` hace:

1. instala/actualiza el core con `make install-core`
2. instala en editable el paquete del dominio desde `./mcps/<dominio>/pyproject.toml`

### Instalar todos los dominios

```bash
make install-mcp-all
```

## 2) Catalogo de MCPs

| MCP binary | Server name | Dominio |
|---|---|---|
| `forge-mcp-file` | `forgetools-file` | Files, search, edit, diff, text, template, json, config |
| `forge-mcp-git` | `forgetools-git` | Git + GitHub |
| `forge-mcp-docs` | `forgetools-docs` | Docs + OpenAPI + web extraction |
| `forge-mcp-specnative` | `forgetools-specnative` | SpecNative + context + ether |
| `forge-mcp-linux` | `forgetools-linux` | process + diag + net + shell + secrets |
| `forge-mcp-java` | `forgetools-java` | java + lint + test + security |
| `forge-mcp-websearch` | `forgetools-websearch` | websearch + web |
| `forge-mcp-containers` | `forgetools-containers` | docker + k8s + helm |
| `forge-mcp-build` | `forgetools-build` | go + npm + cargo + make |
| `forge-mcp-data` | `forgetools-data` | db |

## 3) Capacidades por dominio

### file
- Lectura/arbol/diff/checksum de archivos.
- Busqueda (`grep`, `find-files`, `todo`) y reemplazo.
- Edicion estructurada (`insert`, `replace-lines`, `bulk-rename`).
- Utilidades `config`, `json`, `template`.

### git
- Estado, historial, diff, ramas, stash, conflicts, tags.
- Worktrees, submodulos, commit, cherry-pick.
- PR/issues/actions/releases con `gh`.

### docs
- Generacion de changelog.
- Parseo de especificaciones OpenAPI.
- Extraccion de contenido web (`web_fetch`).

### specnative
- Estado de iniciativas y flujo spec-first.
- Lectura de contexto del repositorio.
- Catalogo del ecosistema ether.

### linux
- Procesos, puertos, inspeccion y kill.
- Diagnostico de entorno (`diag health/env/port`).
- HTTP checks y shell controlado.
- Escaneo de secretos.

### java
- Maven/Gradle, modulos, stacktraces, reports.
- Lint y seguridad (checkstyle, spotbugs, owasp).
- Resources:
  - `forge://java/standards/project-structure`
  - `forge://java/standards/testing-strategy`
  - `forge://java/standards/dependency-policy`
- Prompts:
  - `java_new_service_scaffold(service_name, package_base)`
  - `java_code_review_strict(scope)`

### websearch
- Busqueda con DDGS:
  - `websearch_ddg_search`
- Navegacion/extraccion web:
  - `websearch_visit`
  - `web_fetch` (legacy, expuesto en este dominio)

### containers
- Docker: ps, build, logs, inspect, exec, compose.
- Kubernetes: pods, logs, rollout, contexts.
- Helm: status, install, upgrade, diff.

### build
- Go: build, test, mod.
- npm: run, install, audit.
- Cargo: build, test, check.
- Make: run targets.

### data
- DB query.
- DB schema inspection.
- DB migrations.

## 4) Uso rapido

### Levantar MCP por dominio

```bash
forge-mcp-file
forge-mcp-git
forge-mcp-docs
forge-mcp-specnative
forge-mcp-linux
forge-mcp-java
forge-mcp-websearch
forge-mcp-containers
forge-mcp-build
forge-mcp-data
```

### Consultar catalogo del MCP activo

```text
forge://catalog
```

### Ejemplos CLI (websearch)

```bash
forge websearch ddg-search --query "openapi mcp examples" --max-results 5
forge websearch ddg-search --query "java release notes" --source news --max-results 5
forge websearch visit --url https://example.com --include-links
```

## 5) Configuracion de clientes

Los ejemplos usan binarios desde `.venv/bin` para no depender del `PATH` del cliente.

### Codex

Agrega los servidores al archivo de configuracion MCP de Codex que uses en tu entorno:

```toml
[mcp_servers.forgetools_file]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-file"
args = []

[mcp_servers.forgetools_git]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-git"
args = []

[mcp_servers.forgetools_docs]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-docs"
args = []

[mcp_servers.forgetools_specnative]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-specnative"
args = []

[mcp_servers.forgetools_linux]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-linux"
args = []

[mcp_servers.forgetools_java]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-java"
args = []

[mcp_servers.forgetools_websearch]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-websearch"
args = []

[mcp_servers.forgetools_containers]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-containers"
args = []

[mcp_servers.forgetools_build]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-build"
args = []

[mcp_servers.forgetools_data]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-data"
args = []
```

### Claude Code

Usa `claude mcp add` para registrar cada servidor por dominio:

```bash
claude mcp add forgetools-file -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-file
claude mcp add forgetools-git -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-git
claude mcp add forgetools-docs -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-docs
claude mcp add forgetools-specnative -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-specnative
claude mcp add forgetools-linux -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-linux
claude mcp add forgetools-java -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-java
claude mcp add forgetools-websearch -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-websearch
claude mcp add forgetools-containers -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-containers
claude mcp add forgetools-build -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-build
claude mcp add forgetools-data -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-data
```

### opencode

```json
{
  "mcp": {
    "forgetools-file": { "type": "local", "command": ["forge-mcp-file"] },
    "forgetools-git": { "type": "local", "command": ["forge-mcp-git"] },
    "forgetools-docs": { "type": "local", "command": ["forge-mcp-docs"] },
    "forgetools-specnative": { "type": "local", "command": ["forge-mcp-specnative"] },
    "forgetools-linux": { "type": "local", "command": ["forge-mcp-linux"] },
    "forgetools-java": { "type": "local", "command": ["forge-mcp-java"] },
    "forgetools-websearch": { "type": "local", "command": ["forge-mcp-websearch"] },
    "forgetools-containers": { "type": "local", "command": ["forge-mcp-containers"] },
    "forgetools-build": { "type": "local", "command": ["forge-mcp-build"] },
    "forgetools-data": { "type": "local", "command": ["forge-mcp-data"] }
  }
}
```

### VS Code

En un workspace, agrega `.vscode/mcp.json`:

```json
{
  "servers": {
    "forgetools-file": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-file",
      "args": []
    },
    "forgetools-git": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-git",
      "args": []
    },
    "forgetools-docs": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-docs",
      "args": []
    },
    "forgetools-specnative": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-specnative",
      "args": []
    },
    "forgetools-linux": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-linux",
      "args": []
    },
    "forgetools-java": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-java",
      "args": []
    },
    "forgetools-websearch": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-websearch",
      "args": []
    },
    "forgetools-containers": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-containers",
      "args": []
    },
    "forgetools-build": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-build",
      "args": []
    },
    "forgetools-data": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-data",
      "args": []
    }
  }
}
```
