# Guia de seleccion de MCP

Este documento define que MCP conviene habilitar en cada tipo de agente. El objetivo es reducir el contexto inicial y mantener disponibles solo las capacidades necesarias para el trabajo actual.

## Regla principal

No es necesario desinstalar los MCP que no se usan. La instalacion y la habilitacion son decisiones distintas:

- `make install-mcp-all` instala los 20 paquetes de dominio en `.venv`.
- El cliente solo envia al agente los MCP registrados en su configuracion.
- Para reducir contexto, registra pocos servidores y habilita los demas solo para tareas que los necesiten.

La cantidad de herramientas, resources y prompts es una referencia de superficie de contexto. El consumo real depende del cliente, del modelo y de si el servidor carga la metadata completa al iniciar.

## Conjunto recomendado

### Nucleo universal

Para casi cualquier agente que trabaje en un repositorio:

| MCP | Por que es default | Superficie aproximada |
|---|---|---:|
| `file` | Leer, buscar, editar, comparar y validar archivos del repositorio. Es la base de cualquier cambio de codigo. | 22 tools, 3 resources, 2 prompts |
| `git` | Revisar estado, diff, historial, ramas, worktrees, commits y flujos GitHub. Protege el ciclo de cambio y entrega. | 39 tools, 12 resources, 17 prompts |

Instalacion:

```bash
make install-mcp-file
make install-mcp-git
```

Este es el perfil adecuado para un agente general de mantenimiento, bug fixing o exploracion de un repositorio.

### Nucleo para proyectos gestionados con SpecNative

Agregar `specnative` cuando el repositorio contiene `spec-native/`, usa iniciativas, tareas, decisiones o contexto gobernado por SpecNative.

| MCP | Por que agregarlo | Superficie aproximada |
|---|---|---:|
| `specnative` | Provee contexto del producto y arquitectura, estado de iniciativas, board, backlog, artifacts, continuidad de sesion y prompts de workflow. | 13 tools, 26 resources, 18 prompts |

Instalacion:

```bash
make install-mcp-specnative
```

Para este repositorio, el perfil recomendado es:

```text
file + git + specnative
```

No debe habilitarse `specnative` en agentes que solo hagan tareas puntuales sobre repositorios que no usan su estructura, porque sus resources y prompts agregan una superficie considerable.

## Perfiles por caso de uso

Activa el nucleo universal y agrega solo el perfil que corresponda.

| Perfil | MCP adicionales | Cuando usarlo |
|---|---|---|
| Python | `python`, `quality` | Proyectos Python con `uv`, pytest, Ruff, mypy, cobertura o escaneo de secretos. |
| Java | `java`, `quality` | Maven/Gradle, JDT, reportes JUnit, stacktraces, Checkstyle, SpotBugs u OWASP. |
| Frontend | `frontend`, `quality` | Aplicaciones web donde se necesita detectar stack, revisar assets, ejecutar npm y validar lint/tests. |
| Polyglot build | `build`, `deps` | Proyectos Go, Node, Rust, Make o cuando se investiga metadata de paquetes y upgrades. |
| Documentacion | `docs` | Changelogs, OpenAPI y extraccion de contenido web sin necesidad de busqueda web general. |
| Office/PDF | `office` | Crear DOCX/PDF, fusionar PDFs, anexar tablas, extraer texto, sellar documentos o generar reportes. |
| Web research | `websearch` | Investigar documentacion, noticias, proyectos o sitios web; usa DDGS y navegacion. |
| Linux local | `linux`, `observability` | Procesos, puertos, memoria, red, salud del host, tail y parseo de logs. |
| Contenedores | `containers` | Docker, Kubernetes y Helm. Activarlo solo cuando el trabajo opera esos runtimes. |
| Bastion Podman | `podman`, opcionalmente `linux` | Publicar, inspeccionar y validar contenedores Podman en bastion bajo la politica de puertos autorizados. |
| Datos | `data` | Consultas, schema y migraciones de bases de datos. |
| Cloud | `cloud` | Verificar la identidad activa de AWS, GCP o Azure antes de operar infraestructura. |
| Release | `release` | Prechecks, changelog y releases de GitHub; normalmente se usa al final del ciclo. |
| IA local | `ai` | Inspeccionar, descargar o ejecutar modelos mediante Ollama. |

Ejemplos de instalacion de perfiles:

```bash
# Python
make install-mcp-python
make install-mcp-quality

# Java
make install-mcp-java
make install-mcp-quality

# Frontend
make install-mcp-frontend
make install-mcp-quality

# Operaciones en bastion
make install-mcp-podman
make install-mcp-linux
make install-mcp-observability
```

## Cuando no usar cada MCP como default

### `docs` y `office`

No son equivalentes. `docs` sirve para changelog, OpenAPI y extraccion web; `office` tiene dependencias y operaciones de PDF/DOCX/XLSX. Habilita `office` solo si el agente realmente manipulara documentos binarios.

### `websearch`

Es util para informacion externa, pero introduce una capacidad de navegacion que no es necesaria para cambios locales. Usalo en investigacion, comparacion de librerias, documentacion que no esta en el repo o informacion actualizada.

### `containers`, `podman`, `cloud` y `linux`

Son MCP operativos. No deben estar habilitados en un agente dedicado solo a editar y revisar codigo. Ademas, aumentan el riesgo operativo porque algunas herramientas interactuan con procesos, runtimes, clusters o identidades activas.

### `release`

Debe habilitarse cerca de una entrega. Sus capacidades se solapan con GitHub y changelog, por lo que mantenerlo siempre activo agrega superficie sin beneficio durante desarrollo normal.

### `deps`

Es de investigacion de dependencias. No hace falta para cada cambio; agregalo cuando el objetivo sea comparar versiones, revisar metadata de PyPI/npm/Maven o preparar upgrades.

### `ai`

Solo es relevante si el equipo opera Ollama o modelos locales. No aporta valor a un agente de codigo que usa un modelo remoto.

## Matriz de decision

Usa esta secuencia antes de registrar un MCP en el cliente:

1. ¿El agente necesita leer o modificar archivos? Habilita `file`.
2. ¿El trabajo ocurre en un repositorio Git? Habilita `git`.
3. ¿El repo usa `spec-native/` o requiere contexto gobernado? Agrega `specnative`.
4. ¿Hay un lenguaje o runtime dominante? Agrega un solo perfil de lenguaje: `python`, `java`, `frontend` o `build`.
5. ¿La tarea requiere validacion automatizada? Agrega `quality`.
6. ¿La tarea toca sistemas externos? Agrega el MCP operativo especifico y retiralo al terminar.
7. ¿La tarea requiere informacion actual de internet? Agrega `websearch` durante esa sesion.

Evita activar dos MCP que cubren la misma fase si no existe una necesidad concreta. Por ejemplo, para una tarea Java normal basta `java` y `quality`; `deps` se agrega solo para investigacion de dependencias y `release` solo para entrega.

## Configuracion minima sugerida

### Agente general

```json
{
  "mcp": {
    "forgetools-file": { "type": "local", "command": ["forge-mcp-file"] },
    "forgetools-git": { "type": "local", "command": ["forge-mcp-git"] }
  }
}
```

### Agente de este repositorio

```json
{
  "mcp": {
    "forgetools-file": { "type": "local", "command": ["forge-mcp-file"] },
    "forgetools-git": { "type": "local", "command": ["forge-mcp-git"] },
    "forgetools-specnative": { "type": "local", "command": ["forge-mcp-specnative"] }
  }
}
```

La sintaxis exacta cambia entre Codex, Claude Code, opencode y VS Code. Los ejemplos completos estan en [mcp-usage-installation.md](./mcp-usage-installation.md). Registra solamente los bloques del perfil elegido.

## Instalacion versus habilitacion

Para preparar todos los binarios una sola vez:

```bash
make install-mcp-all
just mcp-list
```

Despues configura solo los servidores necesarios en cada agente. Si prefieres mantener el entorno minimo, instala unicamente los targets seleccionados:

```bash
make install-mcp-file
make install-mcp-git
make install-mcp-specnative
```

`make install-mcp` es un alias del instalador monolitico de todos los dominios; no debe confundirse con el perfil minimo. Para trabajo diario es preferible instalar o habilitar por dominio.

## Presets recomendados

| Preset | MCP habilitados | Objetivo |
|---|---|---|
| `minimal` | `file`, `git` | Cambios locales y mantenimiento general. |
| `specnative` | `file`, `git`, `specnative` | Desarrollo guiado por especificaciones en este ecosistema. |
| `python` | `file`, `git`, `python`, `quality` | Desarrollo y validacion Python. |
| `java` | `file`, `git`, `java`, `quality` | Desarrollo y validacion Java. |
| `web` | `file`, `git`, `frontend`, `quality`, opcional `websearch` | Frontend y consulta de documentacion externa. |
| `operations` | `file`, `git`, `linux`, `observability`, `containers`, opcional `cloud` | Diagnostico y despliegue; usar con permisos controlados. |
| `documents` | `file`, `git`, `docs`, `office` | Documentacion tecnica y archivos PDF/DOCX. |

Como regla practica, empieza con `minimal` y cambia temporalmente al preset de la tarea. El preset `specnative` es el default recomendado para los agentes que trabajen dentro de este repositorio.

## Fuente de verdad

El catalogo generado y los conteos actuales se encuentran en [generated/mcp-capabilities.md](./generated/mcp-capabilities.md). La instalacion y configuracion detallada estan en [mcp-usage-installation.md](./mcp-usage-installation.md), y la descripcion completa de cada dominio en [mcp-domains.md](./mcp-domains.md).
