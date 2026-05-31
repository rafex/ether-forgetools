# MCP Domains Guide

Guia de uso para los MCP disponibles en `forgetools`, con listado de capacidades por dominio.

## Requisitos

```bash
make install-mcp
```

`make install-mcp` instala todos los MCP de dominio. El paquete base se instala con `make install-core`.
Cada MCP de dominio se instala desde su propio `pyproject.toml` en `mcps/<dominio>/`.

## Instalacion por dominio

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

Instalar todos los MCP de dominio:

```bash
make install-mcp-all
```

## Mapeo de pyproject por MCP

| MCP | pyproject.toml |
|---|---|
| `forge-mcp-file` | `./mcps/file/pyproject.toml` |
| `forge-mcp-git` | `./mcps/git/pyproject.toml` |
| `forge-mcp-docs` | `./mcps/docs/pyproject.toml` |
| `forge-mcp-specnative` | `./mcps/specnative/pyproject.toml` |
| `forge-mcp-linux` | `./mcps/linux/pyproject.toml` |
| `forge-mcp-java` | `./mcps/java/pyproject.toml` |
| `forge-mcp-websearch` | `./mcps/websearch/pyproject.toml` |
| `forge-mcp-containers` | `./mcps/containers/pyproject.toml` |
| `forge-mcp-build` | `./mcps/build/pyproject.toml` |
| `forge-mcp-data` | `./mcps/data/pyproject.toml` |

## MCP disponibles

### 1) Dominio File

- Binario: `forge-mcp-file`
- Server name: `forgetools-file`
- Categorias: `fs`, `search`, `edit`, `diff`, `text`, `template`, `json`, `config`
- Casos de uso:
  - lectura/escritura estructurada
  - busqueda/refactor
  - validacion/configuracion de repos

Uso:

```bash
forge-mcp-file
```

### 2) Dominio Git/GitHub

- Binario: `forge-mcp-git`
- Server name: `forgetools-git`
- Categorias: `git`, `gh`
- Casos de uso:
  - cambios locales, ramas, worktrees, tags, submodulos
  - PRs/issues/actions/releases en GitHub

Uso:

```bash
forge-mcp-git
```

### 3) Dominio Docs

- Binario: `forge-mcp-docs`
- Server name: `forgetools-docs`
- Categorias: `docs`, `openapi`, `web`
- Casos de uso:
  - changelog
  - parseo OpenAPI
  - extraccion de contenido web

Uso:

```bash
forge-mcp-docs
```

### 4) Dominio SpecNative

- Binario: `forge-mcp-specnative`
- Server name: `forgetools-specnative`
- Categorias: `specnative`, `context`, `ether`
- Casos de uso:
  - estado/iniciativas SpecNative
  - contexto del repo para agentes
  - catalogo del ecosistema ether

Uso:

```bash
forge-mcp-specnative
```

### 5) Dominio Linux

- Binario: `forge-mcp-linux`
- Server name: `forgetools-linux`
- Categorias: `process`, `diag`, `net`, `shell`, `secrets`
- Casos de uso:
  - procesos/puertos
  - salud de entorno
  - requests HTTP de verificacion
  - comandos shell controlados
  - escaneo de secretos

Uso:

```bash
forge-mcp-linux
```

### 6) Dominio Java (especial)

- Binario: `forge-mcp-java`
- Server name: `forgetools-java`
- Categorias: `java`, `lint`, `test`, `security`
- Casos de uso:
  - build/test Java y analisis de stacktraces
  - calidad y seguridad (checkstyle/spotbugs/owasp)
- guia de estandares y prompts de workflow

Uso:

```bash
forge-mcp-java
```

### 7) Dominio WebSearch

- Binario: `forge-mcp-websearch`
- Server name: `forgetools-websearch`
- Categorias: `websearch`, `web`
- Casos de uso:
  - busqueda web con DuckDuckGo (DDGS)
  - lectura/navegacion de paginas para extraccion estructurada

Uso:

```bash
forge-mcp-websearch
```

### 8) Dominio Containers

- Binario: `forge-mcp-containers`
- Server name: `forgetools-containers`
- Categorias: `docker`, `k8s`, `helm`
- Casos de uso:
  - contenedores Docker
  - diagnostico Kubernetes
  - operaciones Helm

Uso:

```bash
forge-mcp-containers
```

### 9) Dominio Build

- Binario: `forge-mcp-build`
- Server name: `forgetools-build`
- Categorias: `go`, `npm`, `cargo`, `make`
- Casos de uso:
  - build/test Go
  - npm run/install/audit
  - cargo build/test/check
  - ejecucion de targets Make

Uso:

```bash
forge-mcp-build
```

### 10) Dominio Data

- Binario: `forge-mcp-data`
- Server name: `forgetools-data`
- Categorias: `db`
- Casos de uso:
  - queries
  - schema inspection
  - migrations

Uso:

```bash
forge-mcp-data
```

## Capacidades especiales de `mcp-websearch`

### Tools

- `websearch_ddg_search`
- `websearch_visit`
- `web_fetch` (legacy del dominio web, tambien disponible aqui)

### Ejemplos CLI

```bash
# Search
forge websearch ddg-search --query "openapi mcp examples" --max-results 5

# News search
forge websearch ddg-search --query "java 2026 release" --source news --max-results 5

# Visit/extract
forge websearch visit --url https://example.com --include-links
```

## Capacidades especiales de `mcp-java`

### Resources

- `forge://java/standards/project-structure`
- `forge://java/standards/testing-strategy`
- `forge://java/standards/dependency-policy`

### Prompts

- `java_new_service_scaffold(service_name, package_base)`
- `java_code_review_strict(scope)`

### Documentos fuente

- `docs/java/standards/project-structure.md`
- `docs/java/standards/testing-strategy.md`
- `docs/java/standards/dependency-policy.md`

## Resource catalog comun

Todos los MCP por dominio exponen:

- `forge://catalog`

Este resource lista tools disponibles en ese servidor de dominio.

## Configuracion de clientes

La guia completa con ejemplos para Codex, Claude Code, opencode y VS Code esta en:

- `docs/mcp-usage-installation.md`

Ejemplo compacto para opencode:

```json
{
  "mcp": {
    "forgetools-file": {
      "type": "local",
      "command": ["forge-mcp-file"]
    },
    "forgetools-git": {
      "type": "local",
      "command": ["forge-mcp-git"]
    },
    "forgetools-docs": {
      "type": "local",
      "command": ["forge-mcp-docs"]
    },
    "forgetools-specnative": {
      "type": "local",
      "command": ["forge-mcp-specnative"]
    },
    "forgetools-linux": {
      "type": "local",
      "command": ["forge-mcp-linux"]
    },
    "forgetools-java": {
      "type": "local",
      "command": ["forge-mcp-java"]
    },
    "forgetools-websearch": {
      "type": "local",
      "command": ["forge-mcp-websearch"]
    },
    "forgetools-containers": {
      "type": "local",
      "command": ["forge-mcp-containers"]
    },
    "forgetools-build": {
      "type": "local",
      "command": ["forge-mcp-build"]
    },
    "forgetools-data": {
      "type": "local",
      "command": ["forge-mcp-data"]
    }
  }
}
```

## Comandos utiles

Levantar manualmente un MCP de dominio por stdio:

```bash
forge-mcp-websearch
```

Inspeccionar herramientas via catalog del MCP activo:

```text
forge://catalog
```
