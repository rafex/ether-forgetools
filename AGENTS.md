# AGENTS.md — Guía para agentes de código que usan forgetools

> Este archivo define cómo un agente de IA (OpenCode, Claude Code, Aider, etc.)
> debe usar el toolkit **forgetools**: una colección de scripts Python que envuelven
> herramientas CLI comunes y devuelven salida estructurada en JSON.

---

## Principio fundamental

**Nunca ejecutes comandos raw de shell si forgetools tiene un script para eso.**
Los scripts de forgetools devuelven JSON estructurado, manejan errores con contexto,
y te dan sugerencias cuando algo falla. Son más seguros, más predecibles y más
fáciles de interpretar que la salida cruda de git, kubectl, grep, etc.

---

## Convención de salida

Cada script devuelve un objeto `ForgeResult` en JSON:

```json
{
  "ok": true,
  "tool": "git.status",
  "data": { ... },
  "errors": [],
  "duration_ms": 42
}
```

En caso de error:

```json
{
  "ok": false,
  "tool": "git.status",
  "data": null,
  "errors": ["fatal: not a git repository"],
  "duration_ms": 5,
  "suggestion": "Ejecuta este comando dentro de un repositorio git"
}
```

**Regla:** Siempre verifica el campo `ok` antes de usar `data`. Si `ok` es `false`, lee `errors` y `suggestion` para decidir cómo proceder.

---

## Politica local obligatoria

### Podman Port Allocation Policy (Bastion)

La politica versionada vive en `docs/policies/podman-port-allocation-bastion.md` y tiene prioridad sobre defaults, documentacion externa y ejemplos generados.

Cuando generes o modifiques artefactos para `bastion` que publiquen puertos con Podman, debes:

- usar solo estos rangos de host:
  - `30000-30099` para web/frontend
  - `30100-30199` para api/backend
  - `30200-30299` para database
  - `30300-30399` para temporal/experimental
- inspeccionar puertos ocupados con `podman ps --format '{{.Ports}}'`
- elegir el primer puerto libre del rango correspondiente
- fallar si el rango esta lleno

Nunca uses `-p 80:80`, `-p 443:443`, `-p 8080:8080`, puertos aleatorios, ni puertos fuera de los rangos permitidos sin autorizacion explicita.

---

## Cómo invocar los scripts

Tienes tres formas. Usa la que mejor encaje en tu contexto:

### Opción A — CLI individual (recomendada para agentes)

```bash
python -m forgetools.git.status
python -m forgetools.git.log --max-count 10
python -m forgetools.search.grep --pattern "TODO" --path ./src
python -m forgetools.k8s.pods --namespace production
python -m forgetools.java.maven --goal test --module core
```

### Opción B — CLI unificado

```bash
forge git status
forge git log --max-count 10
forge search grep --pattern "TODO" --path ./src
forge k8s pods -n production
```

### Opción C — Import en Python (para scripts compuestos)

```python
from forgetools.git import status, log
from forgetools.search import grep

result = status.run()
if result.ok:
    print(result.data["branch"])
```

### Flag `--raw`

Si necesitas la salida sin el envoltorio ForgeResult (solo los datos crudos), agrega `--raw`:

```bash
python -m forgetools.git.status --raw
```

### Flag `--cwd`

Para operar en un directorio diferente al actual:

```bash
python -m forgetools.git.status --cwd /ruta/al/proyecto
```

---

## Catálogo de herramientas

### 🔀 Git (`forgetools.git`)

| Script | Qué hace | Cuándo usarlo |
|---|---|---|
| `git.status` | Estado del repo con branch, staged, unstaged, conflictos | Antes de cualquier operación git, para entender el estado actual |
| `git.log` | Historial de commits con autor, fecha, mensaje, archivos | Para entender qué cambió recientemente |
| `git.diff` | Diff estructurado con archivos, líneas añadidas/eliminadas | Para revisar cambios antes de commit o PR |
| `git.branch` | Lista ramas, rama actual, tracking info | Para navegar entre ramas o crear nuevas |
| `git.stash` | Listar, guardar, aplicar stashes | Para guardar trabajo temporal |
| `git.blame` | Blame por archivo con autor y commit por línea | Para entender quién cambió qué y por qué |
| `git.conflicts` | Lista archivos en conflicto con marcadores | Para resolver merge conflicts |

**Ejemplos de uso:**

```bash
# Ver qué archivos han cambiado
python -m forgetools.git.status

# Últimos 5 commits del archivo actual
python -m forgetools.git.log --max-count 5 --path src/main/App.java

# Diff de lo que está staged
python -m forgetools.git.diff --staged

# Blame de un archivo específico
python -m forgetools.git.blame --file src/service/UserService.java --lines 50-80
```

---

### 🐙 GitHub (`forgetools.gh`)

Requiere: `gh` CLI autenticado.

| Script | Qué hace | Cuándo usarlo |
|---|---|---|
| `gh.pr_create` | Crea un PR con título, body, reviewers | Cuando el código está listo para review |
| `gh.pr_list` | Lista PRs abiertos con estado y checks | Para ver qué PRs hay pendientes |
| `gh.pr_review` | Ver comentarios y estado de review de un PR | Para entender feedback de reviewers |
| `gh.pr_diff` | Obtener el diff de un PR específico | Para revisar los cambios de un PR |
| `gh.issue_list` | Lista issues con labels y asignados | Para buscar trabajo pendiente |
| `gh.issue_create` | Crea un issue con título, body, labels | Para reportar bugs o pedir features |
| `gh.repo_info` | Info del repo: descripción, lenguaje, estrellas | Para entender el contexto del proyecto |
| `gh.actions` | Estado de los workflows de CI/CD | Para verificar si los builds pasan |

**Ejemplos de uso:**

```bash
# Crear PR desde la branch actual
python -m forgetools.gh.pr_create --title "feat: add user auth" --body "Implements JWT auth" --reviewer "teammate"

# Ver PRs abiertos
python -m forgetools.gh.pr_list --state open

# Estado de CI/CD
python -m forgetools.gh.actions --branch main
```

---

### ☸️ Kubernetes (`forgetools.k8s`)

Requiere: `kubectl` configurado con acceso al cluster.

| Script | Qué hace | Cuándo usarlo |
|---|---|---|
| `k8s.pods` | Lista pods con estado, restarts, edad | Para diagnosticar el estado del cluster |
| `k8s.logs` | Logs de un pod/container con filtros | Para investigar errores en producción |
| `k8s.describe` | Describe un recurso con eventos y condiciones | Para entender por qué un pod no arranca |
| `k8s.exec` | Ejecuta un comando dentro de un pod | Para debugging interactivo |
| `k8s.apply` | Aplica un manifiesto YAML | Para deployar cambios |
| `k8s.rollout` | Estado y control de rollouts (status, undo) | Para verificar o revertir deploys |
| `k8s.contexts` | Lista y cambia contextos de kubectl | Para navegar entre clusters/namespaces |
| `k8s.resources` | Uso de CPU/memoria por pod | Para diagnosticar performance |

**Ejemplos de uso:**

```bash
# Pods en estado no-Running
python -m forgetools.k8s.pods --namespace production --status-filter NotRunning

# Últimas 100 líneas de logs con grep
python -m forgetools.k8s.logs --pod api-server-7b4d --lines 100 --grep "ERROR"

# Rollback del último deploy
python -m forgetools.k8s.rollout --deployment api-server --action undo --namespace production
```

---

### 🔍 Search (`forgetools.search`)

| Script | Qué hace | Cuándo usarlo |
|---|---|---|
| `search.grep` | Busca patrones en archivos con contexto | Para encontrar código, TODOs, imports |
| `search.find_files` | Encuentra archivos por nombre/extensión/tamaño | Para localizar archivos en el proyecto |
| `search.search_replace` | Busca y reemplaza en múltiples archivos | Para refactors masivos |
| `search.ripgrep` | Wrapper de `rg` con output estructurado | Alternativa rápida a grep en repos grandes |
| `search.ast_grep` | Búsqueda por patrones AST (si disponible) | Para búsquedas semánticas de código |
| `search.todo` | Encuentra TODOs, FIXMEs, HACKs en el código | Para listar deuda técnica |
| `search.imports` | Analiza imports/dependencies de un archivo | Para entender dependencias |

**Ejemplos de uso:**

```bash
# Buscar todos los TODO con contexto de 3 líneas
python -m forgetools.search.grep --pattern "TODO|FIXME" --path ./src --context 3

# Encontrar todos los archivos Java modificados hoy
python -m forgetools.search.find_files --ext .java --modified-since today

# Reemplazar un import en todo el proyecto
python -m forgetools.search.search_replace --pattern "import com.old.package" --replacement "import com.new.package" --path ./src --dry-run
```

---

### ✏️ Edit (`forgetools.edit`)

| Script | Qué hace | Cuándo usarlo |
|---|---|---|
| `edit.patch` | Aplica un parche a un archivo | Para cambios quirúrgicos línea por línea |
| `edit.insert` | Inserta líneas en una posición específica | Para agregar imports, anotaciones, etc. |
| `edit.replace_lines` | Reemplaza un rango de líneas | Para reescribir bloques de código |
| `edit.bulk_rename` | Renombra archivos en lote con patrón | Para refactors de naming |
| `edit.template` | Genera archivos desde templates | Para scaffolding de clases, tests, configs |
| `edit.format` | Formatea código (delega a formatters) | Para aplicar code style |

**Ejemplos de uso:**

```bash
# Insertar un import después de la línea 3
python -m forgetools.edit.insert --file src/App.java --after-line 3 --content "import com.auth.JwtService;"

# Reemplazar líneas 45-60 con nuevo código
python -m forgetools.edit.replace_lines --file src/App.java --start 45 --end 60 --content-file /tmp/new_code.txt

# Generar una clase Java desde template
python -m forgetools.edit.template --template java-service --name UserService --package com.app.service
```

---

### ☕ Java/Build (`forgetools.java`)

| Script | Qué hace | Cuándo usarlo |
|---|---|---|
| `java.maven` | Ejecuta goals de Maven con output parseado | Para builds, tests, dependency checks |
| `java.gradle` | Ejecuta tasks de Gradle con output parseado | Para builds con Gradle |
| `java.parse_stacktrace` | Parsea stack traces de Java a JSON | Para entender errores rápidamente |
| `java.deps` | Lista dependencias del proyecto | Para auditar o buscar conflictos |
| `java.test_report` | Parsea reportes de test (surefire/JUnit) | Para entender qué tests fallaron y por qué |
| `java.checkstyle` | Ejecuta checkstyle y parsea violaciones | Para revisar code style |

**Ejemplos de uso:**

```bash
# Compilar y ejecutar tests de un módulo
python -m forgetools.java.maven --goal "clean test" --module user-service

# Parsear un stack trace pegado en un archivo
python -m forgetools.java.parse_stacktrace --file /tmp/error.log

# Ver dependencias con conflictos
python -m forgetools.java.deps --show-conflicts
```

---

### 📁 Filesystem (`forgetools.fs`)

| Script | Qué hace | Cuándo usarlo |
|---|---|---|
| `fs.tree` | Árbol de directorios con filtros inteligentes | Para entender la estructura del proyecto |
| `fs.disk_usage` | Uso de disco por directorio/archivo | Para encontrar qué ocupa espacio |
| `fs.watch` | Vigila cambios en archivos | Para detectar modificaciones |
| `fs.checksum` | Calcula checksums (MD5, SHA256) | Para verificar integridad de archivos |
| `fs.archive` | Crea/extrae archivos tar/zip | Para empaquetar o desempaquetar |
| `fs.read` | Lee archivos con metadatos (encoding, size, lines) | Alternativa segura a cat para agentes |

**Ejemplos de uso:**

```bash
# Árbol excluyendo target/, node_modules/, .git/
python -m forgetools.fs.tree --path . --max-depth 3 --exclude "target,node_modules,.git,.idea"

# Leer un archivo con metadatos
python -m forgetools.fs.read --file src/App.java --lines 1-50
```

---

### 🩺 Diagnostics (`forgetools.diag`)

| Script | Qué hace | Cuándo usarlo |
|---|---|---|
| `diag.tail_logs` | Tail de logs con filtros y parseo | Para investigar errores |
| `diag.parse_error` | Parsea errores comunes (Java, Python, JS) | Para entender stack traces rápido |
| `diag.port_check` | Verifica si un puerto está en uso | Para diagnosticar conflictos de red |
| `diag.env_validate` | Valida variables de entorno requeridas | Para verificar que el entorno está listo |
| `diag.health` | Verifica salud de herramientas requeridas | Para diagnosticar el setup del agente |

**Ejemplos de uso:**

```bash
# Verificar que todas las herramientas necesarias están instaladas
python -m forgetools.diag.health

# Validar variables de entorno para un proyecto
python -m forgetools.diag.env_validate --required "DATABASE_URL,API_KEY,JWT_SECRET"

# Verificar qué proceso usa el puerto 8080
python -m forgetools.diag.port_check --port 8080
```

---

### 🌐 Network (`forgetools.net`)

| Script | Qué hace | Cuándo usarlo |
|---|---|---|
| `net.http_request` | HTTP requests con output estructurado | Para probar APIs |
| `net.health_check` | Verifica endpoints de salud | Para confirmar que servicios están up |
| `net.curl_debug` | Curl con timing detallado | Para diagnosticar latencia |

---

### 📝 Docs (`forgetools.docs`)

| Script | Qué hace | Cuándo usarlo |
|---|---|---|
| `docs.readme_gen` | Genera README desde estructura del proyecto | Para documentar proyectos nuevos |
| `docs.changelog` | Genera changelog desde commits | Para releases |
| `docs.javadoc_extract` | Extrae documentación de JavaDoc | Para entender APIs internas |

---

## Flujos de trabajo comunes

### Flujo 1: Investigar y corregir un bug

```bash
# 1. Entender el estado actual
python -m forgetools.git.status

# 2. Buscar el error en logs de k8s
python -m forgetools.k8s.logs --pod api-server --grep "NullPointerException" --lines 200

# 3. Parsear el stack trace
python -m forgetools.java.parse_stacktrace --stdin < /tmp/stacktrace.txt

# 4. Localizar el archivo y línea del error
python -m forgetools.search.grep --pattern "UserService.getProfile" --path ./src

# 5. Ver el blame de esas líneas
python -m forgetools.git.blame --file src/service/UserService.java --lines 120-140

# 6. Ver el diff del commit que introdujo el bug
python -m forgetools.git.diff --commit abc123

# 7. Corregir el código
python -m forgetools.edit.replace_lines --file src/service/UserService.java --start 125 --end 130 --content-file /tmp/fix.txt

# 8. Ejecutar tests
python -m forgetools.java.maven --goal test --module user-service

# 9. Crear PR
python -m forgetools.gh.pr_create --title "fix: null check in UserService.getProfile" --body "Fixes #423"
```

### Flujo 2: Refactor masivo

```bash
# 1. Encontrar todas las ocurrencias
python -m forgetools.search.grep --pattern "OldClassName" --path ./src --file-ext .java

# 2. Preview del reemplazo (dry run)
python -m forgetools.search.search_replace --pattern "OldClassName" --replacement "NewClassName" --path ./src --dry-run

# 3. Ejecutar el reemplazo
python -m forgetools.search.search_replace --pattern "OldClassName" --replacement "NewClassName" --path ./src

# 4. Renombrar archivos
python -m forgetools.edit.bulk_rename --path ./src --pattern "OldClassName" --replacement "NewClassName"

# 5. Verificar que compila
python -m forgetools.java.maven --goal compile

# 6. Ejecutar tests
python -m forgetools.java.maven --goal test
```

### Flujo 3: Deploy y verificación

```bash
# 1. Ver estado del cluster
python -m forgetools.k8s.pods --namespace production

# 2. Aplicar manifiestos
python -m forgetools.k8s.apply --file k8s/deployment.yaml --namespace production

# 3. Verificar rollout
python -m forgetools.k8s.rollout --deployment api-server --action status --namespace production

# 4. Health check post-deploy
python -m forgetools.net.health_check --url https://api.example.com/health

# 5. Revisar logs del nuevo pod
python -m forgetools.k8s.logs --deployment api-server --lines 50 --namespace production
```

---

## Reglas para el agente

1. **Siempre usa forgetools si hay un script disponible** en lugar de ejecutar el comando raw.
2. **Siempre parsea la respuesta JSON** y verifica `"ok": true` antes de actuar sobre `data`.
3. **Si `ok` es `false`**, lee `suggestion` y actúa en consecuencia antes de reintentar.
4. **Usa `--dry-run`** cuando esté disponible para operaciones destructivas (search_replace, apply, rollout undo).
5. **Usa `--cwd`** cuando necesites operar en un directorio diferente al workspace actual.
6. **Combina herramientas** en flujos lógicos: status → search → edit → test → commit → PR.
7. **No inventes flags.** Si no estás seguro de qué flags acepta un script, ejecútalo con `--help`.
8. **Prefiere scripts específicos sobre genéricos:** usa `git.status` en lugar de `forge run "git status"`.
9. **Ejecuta `diag.health`** al inicio de una sesión para confirmar que las herramientas necesarias están disponibles.
10. **Nunca ejecutes operaciones destructivas sin confirmar** con el usuario: `k8s.apply`, `rollout undo`, `search_replace` sin `--dry-run`.

---

## Cómo extender forgetools

Si necesitas una herramienta que no existe, puedes crear un nuevo script siguiendo esta estructura:

```
forgetools/<categoria>/<nombre>.py
```

Cada script debe:

1. Tener una función `run(**kwargs) -> ForgeResult`
2. Devolver siempre un `ForgeResult` (nunca print directo)
3. Tener un bloque `if __name__ == "__main__"` que use `make_cli()`
4. Manejar errores y devolver `suggestion` cuando sea útil

```python
"""forgetools.<categoria>.<nombre> — Descripción breve."""

from __future__ import annotations
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command
from forgetools._cli import make_cli


def run(*, cwd: str | None = None, **kwargs) -> ForgeResult:
    with Timer() as t:
        # Tu lógica aquí
        result = run_command(
            "comando args",
            tool_name="categoria.nombre",
            cwd=cwd,
            suggestion_on_fail="Sugerencia útil para el agente",
        )
        return result


if __name__ == "__main__":
    make_cli(
        tool_name="categoria.nombre",
        description="Descripción de lo que hace",
        run_fn=run,
    )
```

---

## Dependencias externas requeridas

| Herramienta | Categoría | Cómo instalar |
|---|---|---|
| `git` | git.* | Pre-instalado en la mayoría de sistemas |
| `gh` | gh.* | `brew install gh` / `apt install gh` |
| `kubectl` | k8s.* | `brew install kubectl` / ver docs oficiales |
| `mvn` | java.maven | `brew install maven` / `apt install maven` |
| `gradle` | java.gradle | `brew install gradle` / wrapper incluido en proyectos |
| `rg` (ripgrep) | search.ripgrep | `brew install ripgrep` / `apt install ripgrep` |

Ejecuta `python -m forgetools.diag.health` para verificar cuáles están disponibles.
