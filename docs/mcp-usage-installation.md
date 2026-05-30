# MCP Usage & Installation

Guia operativa de instalacion y uso de los MCP de `forgetools`.

## 1) Instalacion

### Base

```bash
make install
```

### Con soporte MCP (incluye fastmcp + ddgs)

```bash
make install-mcp
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
```

### Instalar todos los dominios

```bash
make install-mcp-all
```

## 2) Catalogo de MCPs

| MCP binary | Server name | Dominio |
|---|---|---|
| `forge-mcp` | `forgetools` | Monolitico (todas las tools) |
| `forge-mcp-file` | `forgetools-file` | Files, search, edit, diff, text, template, json, config |
| `forge-mcp-git` | `forgetools-git` | Git + GitHub |
| `forge-mcp-docs` | `forgetools-docs` | Docs + OpenAPI + web extraction |
| `forge-mcp-specnative` | `forgetools-specnative` | SpecNative + context + ether |
| `forge-mcp-linux` | `forgetools-linux` | process + diag + net + shell + secrets |
| `forge-mcp-java` | `forgetools-java` | java + lint + test + security |
| `forge-mcp-websearch` | `forgetools-websearch` | websearch + web |

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

## 5) Configuracion ejemplo para opencode

```json
{
  "mcp": {
    "forgetools-file": { "type": "local", "command": ["forge-mcp-file"] },
    "forgetools-git": { "type": "local", "command": ["forge-mcp-git"] },
    "forgetools-docs": { "type": "local", "command": ["forge-mcp-docs"] },
    "forgetools-specnative": { "type": "local", "command": ["forge-mcp-specnative"] },
    "forgetools-linux": { "type": "local", "command": ["forge-mcp-linux"] },
    "forgetools-java": { "type": "local", "command": ["forge-mcp-java"] },
    "forgetools-websearch": { "type": "local", "command": ["forge-mcp-websearch"] }
  }
}
```
