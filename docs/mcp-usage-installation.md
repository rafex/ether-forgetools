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
- `mcps/quality/pyproject.toml`
- `mcps/office/pyproject.toml`
- `mcps/python/pyproject.toml`
- `mcps/frontend/pyproject.toml`
- `mcps/observability/pyproject.toml`
- `mcps/cloud/pyproject.toml`
- `mcps/podman/pyproject.toml`
- `mcps/ai/pyproject.toml`
- `mcps/release/pyproject.toml`
- `mcps/deps/pyproject.toml`

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
for domain in file git docs specnative linux java websearch containers build data quality office python frontend observability cloud podman ai release deps; do
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
make install-mcp-quality
make install-mcp-office
make install-mcp-python
make install-mcp-frontend
make install-mcp-observability
make install-mcp-cloud
make install-mcp-podman
make install-mcp-ai
make install-mcp-release
make install-mcp-deps
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
| `forge-mcp-java` | `forgetools-java` | Java build, JDT, Maven Central and standards |
| `forge-mcp-websearch` | `forgetools-websearch` | websearch + web |
| `forge-mcp-containers` | `forgetools-containers` | docker + k8s + helm |
| `forge-mcp-build` | `forgetools-build` | go + npm + cargo + make |
| `forge-mcp-data` | `forgetools-data` | db |
| `forge-mcp-quality` | `forgetools-quality` | lint + test + security + secrets |
| `forge-mcp-office` | `forgetools-office` | office docs + PDF helpers |
| `forge-mcp-python` | `forgetools-python` | Python + uv + pytest + ruff + mypy |
| `forge-mcp-frontend` | `forgetools-frontend` | frontend diagnostics + npm |
| `forge-mcp-observability` | `forgetools-observability` | logs + observability |
| `forge-mcp-cloud` | `forgetools-cloud` | cloud identity/context |
| `forge-mcp-podman` | `forgetools-podman` | Podman + bastion port policy |
| `forge-mcp-ai` | `forgetools-ai` | Ollama/local AI |
| `forge-mcp-release` | `forgetools-release` | release prechecks + gh/docs |
| `forge-mcp-deps` | `forgetools-deps` | dependency metadata research |

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
- JDT, formato Java y busqueda en Maven Central.
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

### quality
- Lint, tests, coverage, security scans and secret scans.
- Resource: `forge://quality/gates`.

### office
- Markdown to HTML.
- PDF merge and PDF text extraction using local CLIs when available.

### python
- `uv`, pytest, ruff and mypy wrappers.
- Resource: `forge://python/standards/uv`.

### frontend
- Frontend stack detection.
- Broken local asset checks.
- npm wrappers inherited from build tooling.

### observability
- Tail/filter log files.
- Parse JSON lines logs and summarize levels.

### cloud
- Active identity checks for AWS, GCP and Azure CLIs.

### podman
- Podman ps/logs.
- Bastion port range inspection, selection and manifest validation.
- Resources:
  - `forge://podman/policy/bastion-ports`
  - `forge://podman/ports`

### ai
- Ollama list/pull/run.

### release
- Basic release precheck and GitHub release helpers.

### deps
- PyPI and npm metadata lookup.
- Java/Maven and npm dependency helpers.

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
forge-mcp-quality
forge-mcp-office
forge-mcp-python
forge-mcp-frontend
forge-mcp-observability
forge-mcp-cloud
forge-mcp-podman
forge-mcp-ai
forge-mcp-release
forge-mcp-deps
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

[mcp_servers.forgetools_quality]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-quality"
args = []

[mcp_servers.forgetools_office]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-office"
args = []

[mcp_servers.forgetools_python]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-python"
args = []

[mcp_servers.forgetools_frontend]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-frontend"
args = []

[mcp_servers.forgetools_observability]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-observability"
args = []

[mcp_servers.forgetools_cloud]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-cloud"
args = []

[mcp_servers.forgetools_podman]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-podman"
args = []

[mcp_servers.forgetools_ai]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-ai"
args = []

[mcp_servers.forgetools_release]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-release"
args = []

[mcp_servers.forgetools_deps]
command = "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-deps"
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
claude mcp add forgetools-quality -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-quality
claude mcp add forgetools-office -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-office
claude mcp add forgetools-python -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-python
claude mcp add forgetools-frontend -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-frontend
claude mcp add forgetools-observability -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-observability
claude mcp add forgetools-cloud -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-cloud
claude mcp add forgetools-podman -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-podman
claude mcp add forgetools-ai -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-ai
claude mcp add forgetools-release -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-release
claude mcp add forgetools-deps -- /Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-deps
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
    "forgetools-data": { "type": "local", "command": ["forge-mcp-data"] },
    "forgetools-quality": { "type": "local", "command": ["forge-mcp-quality"] },
    "forgetools-office": { "type": "local", "command": ["forge-mcp-office"] },
    "forgetools-python": { "type": "local", "command": ["forge-mcp-python"] },
    "forgetools-frontend": { "type": "local", "command": ["forge-mcp-frontend"] },
    "forgetools-observability": { "type": "local", "command": ["forge-mcp-observability"] },
    "forgetools-cloud": { "type": "local", "command": ["forge-mcp-cloud"] },
    "forgetools-podman": { "type": "local", "command": ["forge-mcp-podman"] },
    "forgetools-ai": { "type": "local", "command": ["forge-mcp-ai"] },
    "forgetools-release": { "type": "local", "command": ["forge-mcp-release"] },
    "forgetools-deps": { "type": "local", "command": ["forge-mcp-deps"] }
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
    },
    "forgetools-quality": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-quality",
      "args": []
    },
    "forgetools-office": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-office",
      "args": []
    },
    "forgetools-python": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-python",
      "args": []
    },
    "forgetools-frontend": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-frontend",
      "args": []
    },
    "forgetools-observability": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-observability",
      "args": []
    },
    "forgetools-cloud": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-cloud",
      "args": []
    },
    "forgetools-podman": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-podman",
      "args": []
    },
    "forgetools-ai": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-ai",
      "args": []
    },
    "forgetools-release": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-release",
      "args": []
    },
    "forgetools-deps": {
      "type": "stdio",
      "command": "/Users/rafex/repository/github/rafex/ether/ether-forgetools/.venv/bin/forge-mcp-deps",
      "args": []
    }
  }
}
```
