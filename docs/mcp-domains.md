# MCP Domains Guide

Guia de uso para los MCP disponibles en `forgetools`, con listado de capacidades por dominio.

## Requisitos

```bash
make install-mcp
```

## Instalacion por dominio

```bash
make install-mcp-file
make install-mcp-git
make install-mcp-docs
make install-mcp-specnative
make install-mcp-linux
make install-mcp-java
```

Instalar todos los MCP de dominio:

```bash
make install-mcp-all
```

## MCP disponibles

### 1) Monolitico

- Binario: `forge-mcp`
- Server name: `forgetools`
- Alcance: todas las tools del registry.

### 2) Dominio File

- Binario: `forge-mcp-file`
- Server name: `forgetools-file`
- Categorias: `fs`, `search`, `edit`, `diff`, `text`, `template`, `json`, `config`
- Casos de uso:
  - lectura/escritura estructurada
  - busqueda/refactor
  - validacion/configuracion de repos

### 3) Dominio Git/GitHub

- Binario: `forge-mcp-git`
- Server name: `forgetools-git`
- Categorias: `git`, `gh`
- Casos de uso:
  - cambios locales, ramas, worktrees, tags, submodulos
  - PRs/issues/actions/releases en GitHub

### 4) Dominio Docs

- Binario: `forge-mcp-docs`
- Server name: `forgetools-docs`
- Categorias: `docs`, `openapi`, `web`
- Casos de uso:
  - changelog
  - parseo OpenAPI
  - extraccion de contenido web

### 5) Dominio SpecNative

- Binario: `forge-mcp-specnative`
- Server name: `forgetools-specnative`
- Categorias: `specnative`, `context`, `ether`
- Casos de uso:
  - estado/iniciativas SpecNative
  - contexto del repo para agentes
  - catalogo del ecosistema ether

### 6) Dominio Linux

- Binario: `forge-mcp-linux`
- Server name: `forgetools-linux`
- Categorias: `process`, `diag`, `net`, `shell`, `secrets`
- Casos de uso:
  - procesos/puertos
  - salud de entorno
  - requests HTTP de verificacion
  - comandos shell controlados
  - escaneo de secretos

### 7) Dominio Java (especial)

- Binario: `forge-mcp-java`
- Server name: `forgetools-java`
- Categorias: `java`, `lint`, `test`, `security`
- Casos de uso:
  - build/test Java y analisis de stacktraces
  - calidad y seguridad (checkstyle/spotbugs/owasp)
  - guia de estandares y prompts de workflow

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

## Configuracion de ejemplo (opencode)

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
    }
  }
}
```

## Comandos utiles

Levantar manualmente un MCP de dominio por stdio:

```bash
forge-mcp-java
```

Inspeccionar herramientas via catalog del MCP activo:

```text
forge://catalog
```
