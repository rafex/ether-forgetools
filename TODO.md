# TODO - MCP Domains Roadmap

Estado actual: el monolito fue eliminado. El repositorio expone MCPs por dominio, instalables con `uv`, con `pyproject.toml` independiente por MCP.

## Inventario actual

MCPs existentes:

- `mcp-ai`
- `mcp-build`
- `mcp-cloud`
- `mcp-containers`
- `mcp-data`
- `mcp-deps`
- `mcp-docs`
- `mcp-file`
- `mcp-frontend`
- `mcp-git`
- `mcp-java`
- `mcp-linux`
- `mcp-observability`
- `mcp-office`
- `mcp-podman`
- `mcp-python`
- `mcp-quality`
- `mcp-release`
- `mcp-specnative`
- `mcp-websearch`

Cobertura actual:

- [x] Todos los tools del registry estan expuestos por algun MCP de dominio.
- [x] Existen `mcps/<dominio>/pyproject.toml` para todos los dominios actuales.
- [x] Existen servidores `forgetools/mcp_<dominio>_server.py` para todos los dominios actuales.
- [x] `make install-mcp` instala todos los dominios via `install-mcp-all`.
- [x] Cada dominio tiene target `make install-mcp-<dominio>`.
- [x] Todos los dominios exponen `forge://catalog`.
- [x] Todos los dominios exponen `forge://capabilities`.
- [x] Los prompts estan distribuidos por dominio mediante `PROMPTS_BY_DOMAIN`.
- [x] Existen resources especificos para `git`, `specnative`, `linux`, `file`, `java`, `containers`, `data`, `podman`, `python` y `quality`.
- [x] `scripts/gen_openapi.py` incluye todos los dominios actuales.
- [x] `openapi/forgetools.json` contiene 158 tools y no tiene summaries vacios.
- [x] La documentacion incluye instalacion y ejemplos de configuracion para Codex, Claude Code, opencode y VS Code.

Pendiente general:

- [ ] Implementaciones profundas por dominio: cloud completo, DOCX/PDF avanzado, browser/headless real y mejoras funcionales por dominio.
- [x] Revisar y ejecutar instalacion editable de todos los MCPs en CI con `uv` en cada cambio relevante.

## Prioridad inmediata

- [x] Crear snapshots de tools/resources/prompts por dominio para detectar regresiones.
- [x] Agregar tests MCP para `tools/list`, `resources/list` y `prompts/list`.
- [x] Generar `capabilities.json` fisico por MCP a partir del servidor vivo.
- [x] Generar documentacion automaticamente desde capabilities.
- [x] Parametrizar `Justfile` para servir cualquier MCP de dominio, no solo `forge-mcp-file`.
- [x] Definir politica de dependencias opcionales por dominio y evitar dependencias no usadas.

## Estado por dominio

### `mcp-file`

Estado actual: agrupa `fs`, `search`, `edit`, `diff`, `text`, `template`, `json` y `config`.

Implementado:

- [x] Lectura, arbol, head/tail, diff, checksum y busqueda de archivos.
- [x] Grep, replace, TODO scan y herramientas de edicion basica.
- [x] Diff JSON/YAML, auditoria de caracteres y validacion/configuracion.

Pendiente:

- [ ] Agregar operaciones seguras de copy/move/delete con `dry_run`.
- [ ] Agregar patch estructurado con preview.
- [ ] Mejorar `fs_find_by_type`: hoy tiene conflicto CLI con `--cwd`.
- [ ] Agregar resources de estructura del workspace y archivos relevantes.
- [ ] Agregar soporte para auditoria de encoding, binarios grandes y line endings.

### `mcp-git`

Estado actual: agrupa `git` y `gh`.

Implementado:

- [x] Status, log, diff, branch, blame, stash, conflicts, tags, cherry-pick, worktree, commit y submodules.
- [x] PRs, issues, releases, Actions, branches y GitHub API basica.
- [x] Resources de status, log, worktrees, branches, PRs abiertos y CI.
- [x] Prompts de review, release, CI, commits, PRs y worktrees.
- [x] Planes para stacked PRs y backports.
- [x] Validacion preflight de rama, remote, working tree y branch protection.
- [x] Estado GitHub agregado: PRs, checks, reviewers, issues y branches.
- [x] Plan multi-commit explicito desde archivos cambiados.
- [x] Worktree workflow para cambios multiples: plan/init/status/sync/integrate/finalize/abort.
- [x] Plan de merge readiness para sesiones worktree.

Pendiente:

- [ ] Agregar ejecucion asistida de stacked PRs con confirmacion explicita.
- [ ] Agregar ejecucion asistida de backports con confirmacion explicita.
- [ ] Agregar convenciones configurables para release branches.

### `mcp-docs`

Estado actual: agrupa documentacion tecnica: `docs`, `openapi` y `web`.

Implementado:

- [x] Changelog desde git.
- [x] Parseo OpenAPI.
- [x] Fetch web basico.

Pendiente:

- [ ] Agregar generacion de README, ADR, changelog extendido y docs de API.
- [ ] Agregar resources de plantillas documentales.
- [ ] Agregar prompts para documentar arquitectura, APIs y decisiones.
- [ ] Mantener PDF/DOCX y reportes de negocio en `mcp-office`.

### `mcp-specnative`

Estado actual: agrupa `specnative`, `context` y `ether`.

Implementado:

- [x] Status, context e initiative.
- [x] Context summarize, diff-summary y repo-size.
- [x] Catalogo Ether.
- [x] Resources de contexto y documentos SpecNative.

Pendiente:

- [ ] Versionar schema de SpecNative como resource formal.
- [ ] Agregar validadores de spec, roadmap, traceability y decisions.
- [ ] Agregar generador de iniciativas desde issue/PR/contexto.
- [ ] Agregar reporte de drift entre specs y codigo.
- [ ] Agregar prompts para refinement, planning, review y cierre.
- [ ] Agregar tests de compatibilidad de documentos SpecNative.

### `mcp-linux`

Estado actual: agrupa `process`, `diag`, `net` y `shell`.

Implementado:

- [x] Procesos, puertos, top, kill e inspect.
- [x] Health/env/port diagnostics.
- [x] HTTP/health checks.
- [x] Shell run.

Pendiente:

- [ ] Agregar IO/disk: `df`, `du`, inodes, mountpoints, file descriptors.
- [ ] Agregar memoria: `free`, vmstat, pressure, top consumers.
- [ ] Agregar red: sockets, DNS, traceroute, TLS inspection.
- [ ] Agregar guardrails para `shell_run` y operaciones destructivas.
- [ ] Mantener logs operacionales avanzados en `mcp-observability`.

### `mcp-java`

Estado actual: enfocado en categoria `java`.

Implementado:

- [x] Maven, Gradle, modulos Maven, Maven Central, stacktrace, test report, format y JDT.
- [x] Resources de Maven Central y coverage.
- [x] Prompts de analisis Java, dependencias Maven y seguridad.

Pendiente:

- [ ] Agregar resources de arquitectura Java por stack: Spring Boot, Quarkus, Micronaut.
- [ ] Agregar prompts de migracion Java, upgrade de Spring y hardening de Maven/Gradle.
- [ ] Agregar deteccion de modulos multi-module y mapas de dependencia.
- [ ] Agregar tool para generar estructura base siguiendo standards locales.
- [ ] Agregar integracion mas fuerte con changelogs de dependencias via `mcp-deps`.

### `mcp-websearch`

Estado actual: agrupa `websearch` y `web`.

Implementado:

- [x] Busqueda DDGS usando paquete `ddgs`.
- [x] Visita/fetch basico de paginas.

Pendiente:

- [ ] Agregar providers alternativos ademas de DDGS.
- [ ] Agregar cache local de busquedas y paginas visitadas.
- [ ] Agregar extraccion de links, metadata, main content y markdown limpio.
- [ ] Agregar robots/rate-limit policy configurable.
- [ ] Agregar navegador real/headless si se necesita JS rendering.
- [ ] Agregar resources de fuentes confiables por dominio.

### `mcp-containers`

Estado actual: agrupa `docker`, `k8s` y `helm`.

Implementado:

- [x] Docker ps/build/logs/inspect/exec/compose.
- [x] Kubernetes pods/logs/rollout/contexts.
- [x] Helm status/install/upgrade/diff.
- [x] Resource de politica Podman bastion para agentes que trabajen con contenedores.

Pendiente:

- [ ] Agregar tools para Docker images, volumes, networks y prune con `dry_run`.
- [ ] Agregar manifests Kubernetes: apply/diff/describe/events/resources.
- [ ] Agregar policy checks para Dockerfile/Containerfile.
- [ ] Integrar validacion de puertos bastion cuando se generen manifests Podman desde este dominio.

### `mcp-build`

Estado actual: agrupa `go`, `npm`, `cargo` y `make`.

Implementado:

- [x] Go build/test/mod.
- [x] npm run/install/audit.
- [x] Cargo build/test/check.
- [x] make run.

Pendiente:

- [ ] Agregar deteccion automatica de build system.
- [ ] Agregar cache de resultados de build/test.
- [ ] Agregar wrappers para pnpm, yarn, bun, turbo y nx.
- [ ] Agregar wrappers para task runners: just, taskfile, mage.
- [ ] Agregar prompts para diagnosticar builds rotos.
- [ ] Evaluar si crece demasiado y conviene separar `mcp-go`, `mcp-node`, `mcp-rust`.

### `mcp-data`

Estado actual: agrupa `db`.

Implementado:

- [x] Query, schema y migrations.
- [x] Resource parametrizado de schema por base.

Pendiente:

- [ ] Agregar conectores reales para Postgres/MySQL via librerias Python opcionales.
- [ ] Agregar introspeccion segura con redaccion de secretos.
- [ ] Agregar explain/analyze para queries.
- [ ] Agregar diff de schemas y drift de migraciones.
- [ ] Agregar soporte Flyway/Liquibase/Alembic.
- [ ] Agregar resources de schemas por base usando templates parametrizados.

### `mcp-quality`

Estado actual: agrupa `lint`, `test`, `security` y `secrets`.

Implementado:

- [x] Checkstyle, ESLint, Pylint y golangci-lint.
- [x] JUnit report, coverage y coverage report.
- [x] OWASP, SpotBugs, ESLint security y secrets scan.
- [x] Resource `forge://quality/gates`.
- [x] Prompts de review, security audit y repo health.

Pendiente:

- [ ] Agregar prompts de code review estricto por lenguaje.
- [ ] Agregar resources de quality gates por tipo de proyecto.
- [ ] Agregar reporte consolidado: lint + tests + coverage + security.
- [ ] Agregar tests de contrato para scanners con dependencias ausentes.

### `mcp-office`

Estado actual: herramientas documentales de negocio.

Implementado:

- [x] Markdown a HTML standalone.
- [x] Merge de PDFs.
- [x] Extraccion de texto de PDF.
- [x] Crear PDF desde Markdown/HTML/texto.
- [x] Crear DOCX desde Markdown/HTML/texto.
- [x] Convertir CSV/XLSX a reportes Markdown/HTML/PDF/DOCX.
- [x] Insertar/anexar hojas y tablas a PDFs.
- [x] Extraer metadatos e imagenes embebidas de PDF.
- [x] Sellar PDFs con texto visible.
- [x] Prompts para reportes ejecutivos y anexos.

Pendiente:

- [ ] Agregar templates DOCX avanzados.
- [ ] Agregar firma digital criptografica de PDFs si aplica.
- [ ] Agregar prompts para actas y documentos tecnicos.

### `mcp-python`

Estado actual: tooling Python con `uv` como runtime estandar.

Implementado:

- [x] Wrapper `python uv`.
- [x] Pytest, Ruff y Mypy.
- [x] Resource `forge://python/standards/uv`.

Pendiente:

- [ ] Ampliar `python uv` para `sync`, `run`, `add`, `remove`, `lock`, `tree` y `pip`.
- [ ] Agregar Pyright y coverage.
- [ ] Inspeccion de `pyproject.toml`.
- [ ] Auditoria de dependencias Python.
- [ ] Resources de estructura recomendada Python.
- [ ] Prompts para crear paquetes, CLIs y tests.

### `mcp-frontend`

Estado actual: herramientas frontend y npm.

Implementado:

- [x] Deteccion frontend basica.
- [x] Validacion de assets basica.
- [x] npm run/install/audit via categorias compartidas.

Pendiente:

- [ ] Ampliar deteccion de stack: Vite, Next, Astro, SvelteKit, Vue, React.
- [ ] Agregar build/test/lint frontend dedicados.
- [ ] Validar rutas/assets rotos con mas contexto.
- [ ] Inspeccionar bundles y tamanos.
- [ ] Integrar screenshots/browser checks cuando haya runtime disponible.
- [ ] Prompts de UI review, accessibility review y responsive QA.

### `mcp-observability`

Estado actual: herramientas operacionales de logs.

Implementado:

- [x] Tail/parse basico de logs.

Pendiente:

- [ ] Agregar wrappers para `lnav`, `journalctl`, `tail`, `grep` estructurado de logs.
- [ ] Parsear logs JSON, nginx, app logs y stacktraces.
- [ ] Health checks multi-endpoint.
- [ ] Diagnostico de latencia basico.
- [ ] Resources de runbooks por servicio.
- [ ] Prompts de incident triage y postmortem.

### `mcp-cloud`

Estado actual: identidad cloud basica.

Implementado:

- [x] `cloud whoami` para AWS, GCP y Azure.

Pendiente:

- [ ] AWS: logs, ecs, ecr, s3, cloudwatch.
- [ ] GCP: logs, storage, cloud run.
- [ ] Azure: logs, container apps.
- [ ] Politicas de seguridad para no ejecutar cambios destructivos sin confirmacion.
- [ ] Resources de cuentas/proyectos activos.

### `mcp-podman`

Estado actual: Podman rootless en `bastion`, separado de Docker.

Implementado:

- [x] `podman ps`.
- [x] `podman logs`.
- [x] `podman ports`.
- [x] Selector automatico de puertos segun `docs/policies/podman-port-allocation-bastion.md`.
- [x] Validacion de manifests/Containerfile contra politica de puertos.
- [x] Resource `forge://podman/ports`.
- [x] Resource `forge://podman/policy/bastion-ports`.

Pendiente:

- [ ] Agregar `podman inspect`, `exec`, `build`, `run` y `create`.
- [ ] Agregar `podman compose`.
- [ ] Agregar `dry_run` y guardrails para acciones destructivas.
- [ ] Prompts para despliegue seguro en bastion.

### `mcp-ai`

Estado actual: herramientas de IA local/remota.

Implementado:

- [x] Ollama basico.

Pendiente:

- [ ] Ollama: modelos, pull, run y embeddings.
- [ ] OpenAI-compatible endpoints locales.
- [ ] Evaluaciones simples de prompts.
- [ ] Gestion de datasets pequenos para pruebas.
- [ ] Resources de modelos disponibles.

### `mcp-release`

Estado actual: releases y versionado cross-repo.

Implementado:

- [x] Precheck de release.
- [x] GitHub releases disponibles via categoria `gh`.
- [x] Changelog disponible via categoria `docs`.
- [x] Prompt de release workflow.

Pendiente:

- [ ] SemVer guiado.
- [ ] Release notes desde commits/PRs.
- [ ] Publicacion de artefactos.
- [ ] Validacion pre-release extendida: clean tree, tests, coverage, security y docs.
- [ ] Prompts para release manager.

### `mcp-deps`

Estado actual: investigacion y actualizacion de dependencias.

Implementado:

- [x] PyPI y npm registry.
- [x] Maven Central via categoria `java`.
- [x] npm audit/install via categoria `npm`.
- [x] Prompts de dependency upgrade y Maven dependency research.

Pendiente:

- [ ] Agregar crates.io y Go proxy.
- [ ] Deteccion de versiones desactualizadas por ecosistema.
- [ ] Analisis de changelog/release notes.
- [ ] Recomendaciones de upgrade seguro.
- [ ] Integracion con `mcp-websearch` para fuentes externas.

## Trabajo transversal

- [x] Crear `capabilities.json` por MCP con tools/resources/prompts/version.
- [x] Generar docs automaticamente desde capabilities.
- [x] Agregar tests MCP para `tools/list`, `resources/list`, `prompts/list`.
- [x] Agregar CI que valida instalacion MCP, compilacion Python y generacion OpenAPI.
- [x] Agregar CI que valida que `scripts/gen_openapi.py` genera 125+ tools.
- [x] Agregar snapshot de tools por dominio para detectar regresiones.
- [x] Normalizar nombres de tools y descripciones.
- [x] Definir politica de dependencias opcionales por dominio.
- [x] Evitar que dominios instalen dependencias no usadas por ese dominio.
- [x] Documentar matriz de compatibilidad Codex, Claude Code, opencode y VS Code.

## Criterios de aceptacion para cambios futuros

Todo nuevo dominio o cambio mayor de dominio debe cumplir:

- [ ] Tiene `mcps/<dominio>/pyproject.toml`.
- [ ] Tiene `forgetools/mcp_<dominio>_server.py`.
- [ ] Tiene target `make install-mcp-<dominio>`.
- [ ] Esta incluido en `make install-mcp-all`.
- [ ] Esta documentado en `docs/mcp-domains.md`.
- [ ] Tiene ejemplo de configuracion en `docs/mcp-usage-installation.md`.
- [ ] Expone `forge://catalog`.
- [ ] Expone `forge://capabilities`.
- [ ] Si tiene prompts/resources, estan registrados por dominio.
- [ ] `scripts/gen_openapi.py` lo incluye si expone tools.
- [ ] Pasa instalacion editable con `uv`.
- [ ] Tiene tests o snapshot MCP para evitar regresiones.
