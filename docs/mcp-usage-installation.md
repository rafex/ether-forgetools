# MCP Usage & Installation

Guia operativa de instalacion y uso de los MCP de `forgetools`.

Antes de instalar o registrar servidores, consulta la [guia de seleccion de MCP](./mcp-selection-guide.md) para elegir un perfil y evitar cargar contexto innecesario.

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
- Busqueda rapida con `fd`/`rg` (`grep`, `find-files`, `todo`) y reemplazo por candidatos.
- `search_grep` usa `rg --json`; para repositorios Git puede usar `git grep` con `tracked_only=true`.
- Lectura de contenido con `bat` en modo plano, con fallback Python.
- Uso de disco con `fs_disk_usage`, preferentemente mediante export JSON de `ncdu`.
- Operaciones de ciclo de vida con `fs_operations`: `info`, `mkdir`, `touch`, `copy`, `move`, `delete`, `archive` y `extract`.
- Las operaciones que modifican archivos generan preview; requieren `--execute --confirm`. El borrado de directorios requiere además `--recursive`.
- Edicion estructurada (`insert`, `replace-lines`, `bulk-rename`).
- Utilidades `config`, `json`, `template`.

Ejemplos de uso rapido:

```bash
forge search find-files --name "service" --ext .py --max-results 50
forge search grep --pattern "TODO|FIXME" --path src --context 2
forge search grep --pattern "Controller" --file-type java --pcre2
forge search grep --pattern "TODO" --tracked-only
forge fs read --file src/main.py --lines 1-80
forge fs disk-usage --path . --max-entries 20
forge fs operations info --path src/main.py
forge fs operations copy --source src/config.example --destination /tmp/config.example
forge fs operations archive --sources src,tests --destination /tmp/project.tar.gz --execute --confirm
forge fs operations extract --source /tmp/project.tar.gz --destination /tmp/project-preview --execute --confirm
```

`copy`, `move`, `delete`, `archive` y `extract` no se ejecutan por accidente: primero muestran el plan. Usa `--overwrite` solo cuando reemplazar el destino sea intencional y `--allow-dangerous` únicamente para una ruta explícitamente autorizada.

### git
- Estado, historial, diff, ramas, stash, conflicts, tags.
- Worktrees, submodulos, commit, cherry-pick.
- Operaciones `git_operations`: inspección (`remote`, `show`, `reflog`), sincronización (`fetch`, `pull`, `push`), ramas (`switch`, `branch-create`, `branch-delete`), recuperación (`restore`, `revert`, `reset`, `reflog`), integración (`merge`, `rebase`), diagnóstico (`bisect`) y mantenimiento (`remote-add`, `remote-remove`, `remote-set-url`, `remote-prune`, `maintenance`).
- Las mutaciones se entregan en preview y requieren `execute=true` mas `confirm=true`.
- PR/issues/actions/releases con `gh`.

Ejemplos de operaciones:

```bash
# Solo lectura
forge git operations remote
forge git operations show --ref HEAD --max-lines 100
forge git operations reflog --count 10

# Primero preview, luego ejecucion explicita
forge git operations push --branch feature/example
forge git operations push --branch feature/example --execute --confirm
forge git operations restore --path src/app.py --execute --confirm
forge git operations branch-create --branch feature/new-api
forge git operations revert --ref HEAD --execute --confirm
forge git operations remote-prune --remote origin --execute --confirm
forge git operations maintenance --maintenance-action count-objects
```

Para `bisect`, indica `--bisect-action start|good|bad|skip|reset`; `good`, `bad` y `skip` pueden recibir `--ref`. Las acciones `revert`, `reset`, `clean`, borrado de ramas y cambios de remotos requieren revisión del preview antes de confirmar.

### docs
- Generacion de changelog.
- Parseo de especificaciones OpenAPI.
- Extraccion de contenido web (`web_fetch`).

### specnative
- Estado de iniciativas y flujo spec-first.
- Compatible con la arquitectura SpecNative v0.9: `spec-native/`, `.specnative/`,
  artefactos `ARCH-*`/`CONV-*`, sesión multi-agente y perfiles oficiales.
- Sincronización remota bajo demanda desde el repositorio y sitios oficiales:
  `specnative_upstream(action="fetch", document="readme-es|readme-en|ai-guide-es|ai-guide-en|website-es|website-ai-es|architecture|mcp|schema")`.
- Releases publicadas: `specnative_upstream(action="releases")`.
- Instalación oficial en un repositorio: primero ejecutar sin efectos
  (`execute=false`); tras revisar target, versión y perfil, repetir con
  `execute=true`. El instalador upstream valida el repositorio git y crea su
  branch de instalación.
- `specnative_artifacts(action="log-architecture|log-convention")` crea una
  propuesta en preview y solo escribe con `write=true`.
- Lectura de contexto del repositorio.
- Board de delivery desde `TASKS.md`: `specnative_board(format="json|markdown|mermaid")`, con columnas `ready`, `in_progress`, `blocked`, `waiting`, `done`.
- Captura segura de backlog: `specnative_backlog(...)` en preview por defecto; si no hay spec ejecutable o faltan criterios/validacion, se registra intake en `spec-native/intake/IDEAS.md`.
- Artefactos persistentes: `specnative_artifacts(action="list-decisions|list-architecture|list-conventions|read|log-architecture|log-convention")`.
- Continuidad multi-agente: `specnative_session(action="resume|checkpoint|update-task|clear")`.
- Al marcar tareas como `done`, `completion_evidence` es obligatorio.
- Resources oficiales:
  - `spec://agents`, `spec://session`, `spec://schema`
  - `spec://context/product`, `spec://context/architecture`, `spec://context/stack`
  - `spec://context/conventions`, `spec://context/commands`, `spec://context/decisions`
  - `spec://context/roadmap`, `spec://context/traceability`
  - `spec://spec-native/pipelines/ci`, `spec://spec-native/pipelines/cd`
  - `spec://pipelines/ci`, `spec://pipelines/cd`
- Prompts oficiales:
  - `specnative`, `capture_backlog`, `init_project_guided`, `start_initiative`, `plan_tasks`, `implement_task`
  - `review_against_spec`, `handoff`, `record_decision`, `record_architecture`,
    `record_convention`, `close_initiative`
- Catalogo del ecosistema ether.

### linux
- Procesos, puertos, inspeccion, consumo y kill.
- Sistema: host, CPU, memoria, uptime y limites.
- Storage: uso, inodos, montajes y rutas de mayor tamaño.
- Logs: journal, dmesg y archivos con salida acotada.
- Servicios systemd con preview y confirmacion para mutaciones.
- Red: interfaces, rutas, DNS y conexiones.
- Preflight de privilegios con `linux_privilege` antes de intentar comandos que puedan requerir `sudo`.
- Diagnostico de entorno (`diag health/env/port`).
- HTTP checks y shell controlado.
- Escaneo de secretos.

Ejemplos:

```bash
forge linux system --action info
forge linux system --action memory
forge linux storage --action usage --path /
forge linux logs --action journal --unit nginx.service --lines 100
forge linux services --action status --unit nginx.service
forge linux services --action restart --unit nginx.service
forge linux network --action routes
forge linux privilege --command "systemctl restart nginx.service"
```

Las mutaciones de servicios requieren `--execute --confirm`; `linux_privilege` no ejecuta el comando inspeccionado y rechaza pipelines/redirecciones. `linux_logs` limita la salida para evitar consumir contexto innecesariamente.

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
- Python: `uv`, `uv pip`, `uv build` y validacion de wheels.
- Java: Maven (`mvnw`), Gradle (`gradlew`) y Ant (`build.xml`).
- Estructura: `Makefile` para build; `Justfile` para task management; helpers separados.

Resources y prompt del dominio:

```text
forge://build/standards/structure
forge://build/standards/make-just-boundaries
forge://build/standards/python
forge://build/standards/java
build_project_scaffold(project_dir=".", project_type="auto", include_just=true)
```

Regla critica: `Justfile` puede invocar targets de `Makefile`, pero `Makefile` nunca puede invocar `Justfile`.

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
- Operaciones locales y remotas sobre Podman: conexiones SSH, `ps`, logs, images e inspect.
- `podman_pull` exige referencias completas para evitar resolucion ambigua de short names:
  - `docker.io/library/nginx:1.27`
  - `ghcr.io/owner/project-api:1.4.0`
- Builds desde `Containerfile`/`Dockerfile` con contexto y `.containerignore`; las imagenes base externas tambien deben usar referencias completas.
- `podman_run` aplica la politica de puertos del bastion y requiere preview + confirmacion explicita.
- Resources:
  - `forge://podman/containerfiles`
  - `forge://podman/containerignore`
  - `forge://podman/image-references`
  - `forge://podman/remote`
  - `forge://podman/policy/bastion-ports`
  - `forge://podman/ports`

Ejemplos:

```text
podman_connection(action="list")
podman_ps(connection="bastion", all=True)
podman_image_reference(image="ghcr.io/owner/project-api:1.4.0")
podman_pull(image="ghcr.io/owner/project-api:1.4.0", connection="bastion")
podman_select_port(category="api", connection="bastion")
podman_run(
  image="ghcr.io/owner/project-api:1.4.0",
  ports=["30180:8080"],
  connection="bastion",
  execute=False,
)
```

Crear una conexion SSH se hace primero en preview y luego con confirmacion:

```text
podman_connection(
  action="add",
  name="bastion",
  destination="ssh://user@bastion/run/user/1000/podman/podman.sock",
  identity="~/.ssh/bastion",
)
podman_connection(
  action="add",
  name="bastion",
  destination="ssh://user@bastion/run/user/1000/podman/podman.sock",
  identity="~/.ssh/bastion",
  execute=True,
  confirm=True,
)
```

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
