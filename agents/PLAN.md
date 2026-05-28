# Plan de separacion de MCP por dominio

## Objetivo

Descomponer el MCP actual de `forgetools` en MCPs por dominio, manteniendo foco en claridad operativa, especializacion por area y evolucion independiente.

---

## Fase 0: Contrato base y alcance

1. Definir naming estable por dominio (`mcp-file`, `mcp-git`, `mcp-github`, `mcp-java`, etc.) y version inicial `v1`.

---

## Fase 1: Extraccion de dominios core

1. `mcp-file`
   - `fs`, `search`, `edit`, `diff`, `text`, `template`, `json`, `config`.
2. `mcp-git`
   - Todo `git.*`.
3. `mcp-github`
   - Todo `gh.*`.
4. `mcp-specnative`
   - `specnative.*`, `context.*` y resources de policy/spec.
5. `mcp-linux`
   - `process.*`, `diag.*`, `net.*`, `shell.*`, `secrets.*`.
6. `mcp-containers`
   - `docker.*`, `k8s.*`, `helm.*` (y luego `podman.*`).
7. `mcp-build`
   - `java`, `go`, `npm`, `cargo`, `make`, `lint`, `test`, `security`.
8. `mcp-docs`
   - `docs.*`, `openapi.*`, `web.*`.
9. `mcp-data`
   - `db.*`.

---

## Fase 2: Dominio especial `mcp-java`

### Alcance funcional

1. Mover o exponer en `mcp-java`:
   - `java.*`
   - `lint.checkstyle`
   - `security.spotbugs`
   - `test.junit-report`
   - cobertura de tests Java.

### Resources (estandares y referencia)

1. `forge://java/standards/project-structure`
2. `forge://java/standards/coding-style`
3. `forge://java/standards/testing-strategy`
4. `forge://java/standards/dependency-policy`
5. `forge://java/standards/error-handling`
6. `forge://java/standards/observability`
7. `forge://java/playbooks/migration`

### Prompts de best practices

1. `java_new_service_scaffold`
2. `java_code_review_strict`
3. `java_refactor_safely`
4. `java_perf_investigation`
5. `java_dependency_upgrade`

### Estructura sugerida de contenido

1. `docs/java/standards/*.md`
2. `docs/java/playbooks/*.md`
3. Los resources del MCP deben leer esos docs como fuente viva.

---

## Fase 3: Capacidades faltantes por dominio

### `mcp-docs`

1. `pdf_create`
2. `pdf_merge`
3. `pdf_split`
4. `pdf_from_markdown`
5. `pdf_metadata`

### `mcp-linux`

1. `linux_mem`
2. `linux_iostat`
3. `linux_sockets`
4. `linux_dns`

### `mcp-containers`

1. `podman_ps`
2. `podman_run`
3. `podman_compose`
4. `podman_ports_next` (alineado con la policy de bastion)

---

## Fase 4: QA y release

1. Tests por MCP:
   - contrato JSON schema
   - casos felices y de error
   - permisos y timeouts.
2. Smoke tests E2E por cliente MCP.
3. Versionado semantico por dominio y changelog.
4. Rollout gradual:
   - internal
   - beta
   - GA.

---

## Orden recomendado de ejecucion

1. `mcp-git` + `mcp-github` (alto uso, bajo riesgo).
2. `mcp-file`.
3. `mcp-java` (con resources/prompts de estandares).
4. `mcp-linux` + `mcp-containers`.
5. `mcp-docs` + refinamiento de `mcp-build` y `mcp-data`.
