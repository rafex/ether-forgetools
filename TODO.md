# TODO - MCP Domains Roadmap

Estado actual: el monolito fue eliminado y existen 10 MCP por dominio:

- `mcp-file`
- `mcp-git`
- `mcp-docs`
- `mcp-specnative`
- `mcp-linux`
- `mcp-java`
- `mcp-websearch`
- `mcp-containers`
- `mcp-build`
- `mcp-data`

Este backlog separa dominios nuevos pendientes de la evolucion necesaria en dominios existentes.

## Estado de implementacion

- [x] Se crearon MCP instalables para `quality`, `office`, `python`, `frontend`, `observability`, `cloud`, `podman`, `ai`, `release` y `deps`.
- [x] `mcp-quality` concentra `lint`, `test`, `security` y `secrets`.
- [x] `mcp-java` quedo enfocado en categoria `java`.
- [x] `mcp-linux` quedo enfocado en `process`, `diag`, `net` y `shell`.
- [x] Todos los MCP exponen `forge://catalog` y `forge://capabilities`.
- [x] `make install-mcp` instala todos los dominios.
- [x] `scripts/gen_openapi.py` incluye todos los dominios.
- [x] CI valida instalacion MCP, compilacion Python y generacion OpenAPI.
- [ ] Quedan pendientes implementaciones profundas marcadas abajo: integraciones cloud completas, generacion DOCX/PDF avanzada, browser real y snapshots de contrato.

## Prioridad inmediata

- [x] Crear `mcp-quality` para mover y agrupar `lint`, `test`, `security`, `secrets` y coverage.
- [x] Crear `mcp-office` o evolucionar `mcp-docs` para PDF, DOCX, hojas, merge de documentos y generacion de reportes.
- [x] Crear soporte Podman real dentro de `mcp-containers` o como `mcp-podman`, respetando `docs/policies/podman-port-allocation-bastion.md`.
- [x] Crear `mcp-python` para tooling Python dedicado: `uv`, pytest, ruff, mypy, packaging y virtualenvs.
- [x] Separar prompts/resources comunes en manifiestos por dominio para que cada MCP declare capacidades, prompts y resources versionados.

## Dominios nuevos sugeridos

### `mcp-quality`

Objetivo: calidad transversal de codigo, tests y seguridad, independiente del lenguaje.

- [ ] Mover desde `mcp-java` las categorias `lint`, `test` y `security`.
- [ ] Mover desde `mcp-linux` la categoria `secrets`.
- [ ] Exponer tools para `coverage`, `junit_report`, `coverage_report`, `eslint`, `pylint`, `golangci`, `checkstyle`, `owasp`, `spotbugs`, `eslint_security`.
- [ ] Agregar prompts de code review estricto por lenguaje.
- [ ] Agregar resources de quality gates por tipo de proyecto.
- [ ] Agregar reporte consolidado: lint + tests + coverage + security.

### `mcp-office`

Objetivo: generacion y transformacion de documentos de negocio.

- [ ] Crear PDF desde Markdown/HTML.
- [ ] Crear DOCX desde Markdown/HTML/templates.
- [ ] Mergear PDFs.
- [ ] Insertar hojas/tablas en PDF.
- [ ] Convertir CSV/XLSX a tablas para reportes.
- [ ] Extraer texto/imagenes/metadatos de PDF.
- [ ] Firmar o sellar PDFs si aplica.
- [ ] Agregar prompts para reportes ejecutivos, anexos, actas y documentos tecnicos.

### `mcp-python`

Objetivo: desarrollo Python con `uv` como runtime estandar.

- [ ] Tools para `uv sync`, `uv run`, `uv add`, `uv remove`, `uv lock`.
- [ ] Tools para pytest, ruff, mypy, pyright y coverage.
- [ ] Inspeccion de `pyproject.toml`.
- [ ] Auditoria de dependencias Python.
- [ ] Resources de estructura recomendada Python.
- [ ] Prompts para crear paquetes, CLIs y tests.

### `mcp-frontend`

Objetivo: aplicaciones frontend y assets web.

- [ ] Tools para detectar stack: Vite, Next, Astro, SvelteKit, Vue, React.
- [ ] Tools para build/test/lint frontend.
- [ ] Tools para validar rutas/assets rotos.
- [ ] Tools para inspeccionar bundles y tamanos.
- [ ] Integrar screenshots/browser checks cuando haya runtime disponible.
- [ ] Prompts de UI review, accessibility review y responsive QA.

### `mcp-observability`

Objetivo: logs, metricas y diagnostico operacional.

- [ ] Agregar wrappers para `lnav`, `journalctl`, `tail`, `grep` estructurado de logs.
- [ ] Parsear logs JSON, nginx, app logs y stacktraces.
- [ ] Health checks multi-endpoint.
- [ ] Diagnostico de latencia basico.
- [ ] Resources de runbooks por servicio.
- [ ] Prompts de incident triage y postmortem.

### `mcp-cloud`

Objetivo: proveedores cloud e infraestructura remota.

- [ ] AWS: sts identity, logs, ecs, ecr, s3, cloudwatch.
- [ ] GCP: auth, logs, storage, cloud run.
- [ ] Azure: account, logs, container apps.
- [ ] Politicas de seguridad para no ejecutar cambios destructivos sin confirmacion.
- [ ] Resources de cuentas/proyectos activos.

### `mcp-podman`

Objetivo: Podman rootless en `bastion`, separado de Docker si se quiere mayor control.

- [ ] `podman ps`, logs, inspect, exec, build, run, create.
- [ ] `podman compose`.
- [ ] Selector automatico de puertos segun `docs/policies/podman-port-allocation-bastion.md`.
- [ ] Validacion de manifests/Containerfile contra politica de puertos.
- [ ] Resource `forge://podman/ports` con puertos ocupados y libres por rango.
- [ ] Prompts para despliegue seguro en bastion.

### `mcp-ai`

Objetivo: herramientas de IA local/remota.

- [ ] Ollama: modelos, pull, run, embeddings.
- [ ] OpenAI-compatible endpoints locales.
- [ ] Evaluaciones simples de prompts.
- [ ] Gestion de datasets pequenos para pruebas.
- [ ] Resources de modelos disponibles.

### `mcp-release`

Objetivo: releases y versionado cross-repo.

- [ ] SemVer, changelog, tags, GitHub Releases.
- [ ] Validacion pre-release: clean tree, tests, coverage, security, docs.
- [ ] Release notes desde commits/PRs.
- [ ] Publicacion de artefactos.
- [ ] Prompts para release manager.

### `mcp-deps`

Objetivo: investigacion y actualizacion de dependencias por ecosistema.

- [ ] Maven Central, npm registry, crates.io, PyPI, Go proxy.
- [ ] Deteccion de versiones desactualizadas.
- [ ] Analisis de changelog/release notes.
- [ ] Recomendaciones de upgrade seguro.
- [ ] Integracion con `mcp-websearch` para fuentes externas.

## Evolucion de dominios actuales

### `mcp-file`

- [ ] Agregar operaciones seguras de copy/move/delete con `dry_run`.
- [ ] Agregar patch estructurado con preview.
- [ ] Agregar diff semantico para JSON/YAML/TOML.
- [ ] Mejorar `fs_find_by_type`: hoy tiene conflicto CLI con `--cwd`.
- [ ] Agregar resources de estructura del workspace y archivos relevantes.
- [ ] Agregar soporte para auditoria de encoding, binarios grandes y line endings.

### `mcp-git`

- [ ] Agregar workflows guiados para stacked PRs y backports.
- [ ] Agregar validacion de rama protegida y remote antes de push/merge.
- [ ] Agregar resource de estado GitHub completo: PRs, checks, reviewers, issues.
- [ ] Mejorar `git_commit` para planes multi-commit con confirmacion explicita.
- [ ] Agregar soporte para etiquetas/release branches con convenciones configurables.
- [ ] Agregar tests de contrato para tools Git/GitHub.

### `mcp-docs`

- [ ] Decidir si queda para documentacion tecnica o si se separa `mcp-office`.
- [ ] Agregar generacion de README, ADR, changelog extendido y docs de API.
- [ ] Agregar generacion de PDF/DOCX si no se crea `mcp-office`.
- [ ] Agregar merge de documentos y anexos.
- [ ] Agregar resources de plantillas documentales.
- [ ] Agregar prompts para documentar arquitectura, APIs y decisiones.

### `mcp-specnative`

- [ ] Versionar schema de SpecNative como resource formal.
- [ ] Agregar validadores de spec, roadmap, traceability y decisions.
- [ ] Agregar generador de iniciativas desde issue/PR/contexto.
- [ ] Agregar reporte de drift entre specs y codigo.
- [ ] Agregar prompts para refinement, planning, review y cierre.
- [ ] Agregar tests de compatibilidad de documentos SpecNative.

### `mcp-linux`

- [ ] Separar `secrets` hacia `mcp-quality`.
- [ ] Agregar IO/disk: `df`, `du`, inodes, mountpoints, file descriptors.
- [ ] Agregar memoria: `free`, vmstat, pressure, top consumers.
- [ ] Agregar red: sockets, DNS, traceroute, TLS inspection.
- [ ] Agregar logs: journalctl/syslog/lnav o mover a `mcp-observability`.
- [ ] Agregar guardrails para `shell_run` y operaciones destructivas.

### `mcp-java`

- [ ] Mantenerlo enfocado en Java; mover calidad transversal a `mcp-quality`.
- [ ] Agregar resources de arquitectura Java por stack: Spring Boot, Quarkus, Micronaut.
- [ ] Agregar prompts de migracion Java, upgrade de Spring, hardening de Maven/Gradle.
- [ ] Agregar deteccion de modulos multi-module y mapas de dependencia.
- [ ] Agregar tool para generar estructura base siguiendo standards locales.
- [ ] Agregar integracion mas fuerte con `maven_central` y changelogs.

### `mcp-websearch`

- [ ] Agregar providers alternativos ademas de DDGS.
- [ ] Agregar cache local de busquedas y paginas visitadas.
- [ ] Agregar extraccion de links, metadata, main content y markdown limpio.
- [ ] Agregar robots/rate-limit policy configurable.
- [ ] Agregar navegador real/headless si se necesita JS rendering.
- [ ] Agregar resources de fuentes confiables por dominio.

### `mcp-containers`

- [ ] Agregar Podman o crear `mcp-podman`.
- [ ] Validar politica de puertos de bastion antes de generar `run/create/compose`.
- [ ] Agregar selector de puerto libre por categoria.
- [ ] Agregar tools para images, volumes, networks y prune con `dry_run`.
- [ ] Agregar manifests Kubernetes: apply/diff/describe/events/resources.
- [ ] Agregar policy checks para Dockerfile/Containerfile.

### `mcp-build`

- [ ] Separar builds por lenguaje si crece demasiado: `mcp-go`, `mcp-node`, `mcp-rust`.
- [ ] Agregar deteccion automatica de build system.
- [ ] Agregar cache de resultados de build/test.
- [ ] Agregar wrappers para pnpm, yarn, bun, turbo y nx.
- [ ] Agregar wrappers para task runners: just, taskfile, mage.
- [ ] Agregar prompts para diagnosticar builds rotos.

### `mcp-data`

- [ ] Agregar conectores reales para Postgres/MySQL via librerias Python opcionales.
- [ ] Agregar introspeccion segura con redaccion de secretos.
- [ ] Agregar explain/analyze para queries.
- [ ] Agregar diff de schemas y drift de migraciones.
- [ ] Agregar soporte Flyway/Liquibase/Alembic.
- [ ] Agregar resources de schemas por base usando templates parametrizados.

## Trabajo transversal

- [ ] Crear `capabilities.json` por MCP con tools/resources/prompts/version.
- [ ] Generar docs automaticamente desde capabilities.
- [ ] Agregar tests MCP para `tools/list`, `resources/list`, `prompts/list`.
- [x] Agregar CI que valide que `make install-mcp` instala todos los dominios.
- [x] Agregar CI que valide que `scripts/gen_openapi.py` genera 125+ tools.
- [ ] Agregar snapshot de tools por dominio para detectar regresiones.
- [ ] Normalizar nombres de tools y descripciones.
- [ ] Definir politica de dependencias opcionales por dominio.
- [ ] Evitar que dominios instalen dependencias no usadas por ese dominio.
- [ ] Documentar matriz de compatibilidad Codex, Claude Code, opencode y VS Code.

## Criterios de aceptacion por nuevo MCP

- [ ] Tiene `mcps/<dominio>/pyproject.toml`.
- [ ] Tiene `forgetools/mcp_<dominio>_server.py`.
- [ ] Tiene target `make install-mcp-<dominio>`.
- [ ] Esta incluido en `make install-mcp-all`.
- [ ] Esta documentado en `docs/mcp-domains.md`.
- [ ] Tiene ejemplo de configuracion en `docs/mcp-usage-installation.md`.
- [ ] Expone `forge://catalog`.
- [ ] Si tiene prompts/resources, estan registrados por dominio.
- [ ] `scripts/gen_openapi.py` lo incluye si expone tools.
- [ ] Pasa instalacion editable con `uv`.
