# ether-forgetools

> Python toolkit of structured scripts for code agents — smarter wrappers around git, gh, kubectl, maven, grep, and more.

Every script returns a `ForgeResult` JSON object with `ok`, `data`, `errors`, and `suggestion` — no raw shell output to parse.

## Local Policies

- Bastion Podman port publication policy: [docs/policies/podman-port-allocation-bastion.md](docs/policies/podman-port-allocation-bastion.md)

## Install

```bash
# Instalar dependencias básicas con uv (Makefile)
make install

# Instalar con soporte MCP (uv + extras)
make install-mcp

# Instalar todos los MCP por dominio
make install-mcp-all

# O usar uv directamente
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e .
uv pip install --python .venv/bin/python -e ".[mcp]"
```

## Usage

### Task Runner (Just)

Usa `just` para tareas de desarrollo, ejecución y utilidades:

```bash
# Mostrar todas las tareas disponibles
just help

# Modo desarrollo (instala + ejecuta servidor)
just dev

# Ejecutar servidor MCP localmente
just serve

# Construir y ejecutar en container
just docker-serve

# Generar documentación OpenAPI
just openapi
```

### Build System (Make)

Usa `make` para gestion de dependencias y construccion estatica (basado en `uv`):

```bash
# Instalar dependencias básicas
make install

# Instalar con soporte MCP
make install-mcp

# Instalar MCP por dominio (ejemplo)
make install-mcp-websearch

# Limpiar artefactos
make clean
```

### Unified CLI

```bash
forge git status
forge search grep --pattern "TODO" --path ./src
forge k8s pods --namespace production
forge java maven --goal "clean test" --module api
forge diag health
```

### Python Module

```bash
python -m forgetools.git.status
python -m forgetools.search.grep --pattern "TODO" --path ./src --context 3
```

### Python Import

```python
from forgetools.git import status
result = status.run(cwd="/path/to/repo")
if result.ok:
    print(result.data["branch"])
```

## Output format

```json
{
  "ok": true,
  "tool": "git.status",
  "data": { "branch": "main", "is_clean": false, "staged": [...] },
  "errors": [],
  "duration_ms": 12
}
```

## Categories

| Category | Scripts |
|---|---|
| `git` | status, log, diff, branch, blame, stash, conflicts |
| `gh` | pr-list, pr-create, pr-review, issue-list, actions |
| `k8s` | pods, logs, rollout, contexts |
| `search` | grep, find-files, replace, todo |
| `edit` | insert, replace-lines, bulk-rename |
| `java` | maven, gradle, stacktrace, test-report |
| `fs` | tree, read |
| `diag` | health, env, port |
| `net` | http, health |
| `docs` | changelog |

See [AGENTS.md](AGENTS.md) for full agent usage guide.

---

## MCP — opencode integration

Exposes all forgetools as MCP tools for use with [opencode](https://opencode.ai) or any MCP-compatible agent.

Domain MCP guide (install, capabilities, config):
- [docs/mcp-domains.md](docs/mcp-domains.md)

### Install with MCP support

```bash
make install-mcp
```

### Configure opencode

Add to `~/.config/opencode/config.json`:

```json
{
  "mcp": {
    "forgetools": {
      "type": "local",
      "command": ["forge-mcp"]
    }
  }
}
```

### MCP binaries disponibles

| Binary | Scope |
|---|---|
| `forge-mcp` | Monolito (todas las tools) |
| `forge-mcp-file` | File/content ops |
| `forge-mcp-git` | Git + GitHub |
| `forge-mcp-docs` | Docs/OpenAPI/Web extraction |
| `forge-mcp-specnative` | SpecNative + context |
| `forge-mcp-linux` | Process/diag/net/shell/secrets |
| `forge-mcp-java` | Java/lint/test/security + resources/prompts |
| `forge-mcp-websearch` | DDGS search + web navigation |

### WebSearch quickstart

```bash
# Buscar en web con DDGS
forge websearch ddg-search --query "specnative mcp" --max-results 5

# Navegar/extraccion de contenido
forge websearch visit --url https://example.com --include-links
```

Every tool returns `{ "ok": bool, "tool": str, "data": ..., "errors": [], "duration_ms": int }`.
