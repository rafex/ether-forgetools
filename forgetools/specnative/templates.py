from __future__ import annotations

"""SpecNative archetypes, spec templates, and decision snippets."""

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "specnative.templates"

BUILTIN_SPEC_TEMPLATES: dict[str, str] = {
    "feature-rest-endpoint": """# Spec: {initiative}

```toml
artifact_type = "spec"
id = "SPEC-{slug_upper}"
state = "draft"
owner = "team"
created_at = "{today}"
updated_at = "{today}"
replaces = "none"
related_tasks = []
related_decisions = []
artifacts = []
validation = []
```

## Resumen

Exponer o modificar un endpoint REST.

## Problema

## Contrato API

- Metodo:
- Path:
- Request:
- Response:
- Errores:

## Criterios de aceptacion

- Dado ... cuando ... entonces ...

## Plan de validacion

- Tests de contrato
- Tests de integracion
""",
    "db-migration": """# Spec: {initiative}

```toml
artifact_type = "spec"
id = "SPEC-{slug_upper}"
state = "draft"
owner = "team"
created_at = "{today}"
updated_at = "{today}"
replaces = "none"
related_tasks = []
related_decisions = []
artifacts = []
validation = []
```

## Resumen

Cambio de esquema o datos.

## Migracion

- Up:
- Down:
- Backfill:

## Riesgos

## Criterios de aceptacion

## Plan de validacion
""",
    "module-refactor": """# Spec: {initiative}

```toml
artifact_type = "spec"
id = "SPEC-{slug_upper}"
state = "draft"
owner = "team"
created_at = "{today}"
updated_at = "{today}"
replaces = "none"
related_tasks = []
related_decisions = []
artifacts = []
validation = []
```

## Resumen

Refactor de modulo sin cambio funcional esperado.

## Problema tecnico

## Invariantes

## Criterios de aceptacion

## Plan de validacion
""",
}

BUILTIN_DECISION_SNIPPETS: dict[str, str] = {
    "jwt-authentication": """### {dec_id} - Autenticacion JWT

- Fecha: {today}
- Estado: `proposed`
- Contexto: El sistema requiere autenticacion stateless entre servicios o clientes.
- Decision: Usar JWT firmado con expiracion corta y refresh controlado.
- Consecuencias: Se debe proteger el secreto/llave, validar expiracion y rotar credenciales.
- Reemplaza: none
""",
    "hexagonal-ports": """### {dec_id} - Puertos hexagonales

- Fecha: {today}
- Estado: `proposed`
- Contexto: El dominio necesita aislar infraestructura y frameworks.
- Decision: Definir puertos de entrada/salida y adaptadores externos.
- Consecuencias: Aumenta la disciplina de capas y reduce acoplamiento a frameworks.
- Reemplaza: none
""",
    "database-choice": """### {dec_id} - Eleccion de base de datos

- Fecha: {today}
- Estado: `proposed`
- Contexto: El producto requiere persistencia con restricciones conocidas.
- Decision: Documentar la base elegida, version y motivo.
- Consecuencias: Futuras iniciativas deben respetar limites operativos y migraciones.
- Reemplaza: none
""",
}

BUILTIN_ARCHETYPES: dict[str, dict[str, str]] = {
    "java-hexagonal": {
        "description": "Java 21 + Spring Boot 3 + Hexagonal Architecture",
        "ARCHITECTURE.md": "# ARCHITECTURE.md\n\n## Modulos principales\n\n- Domain: reglas de negocio puras.\n- Application: casos de uso y puertos.\n- Adapters: HTTP, persistence, messaging.\n\n## Limites y reglas\n\nEl dominio no depende de Spring, JPA ni transporte.\n",
        "STACK.md": "# STACK.md\n\n## Lenguajes y runtimes\n\n- Java 21\n\n## Frameworks y librerias clave\n\n- Spring Boot 3\n- Maven o Gradle segun el proyecto\n",
        "CONVENTIONS.md": "# CONVENTIONS.md\n\n## Estructura de carpetas\n\n- domain\n- application\n- adapters/in\n- adapters/out\n\n## Testing\n\nUnit tests para dominio, integration tests para adapters.\n",
        "COMMANDS.md": "# COMMANDS.md\n\n## Tests\n\n```bash\n./mvnw test\n```\n\n## Build\n\n```bash\n./mvnw verify\n```\n",
        "DECISIONS.md": "# DECISIONS.md\n\n### DEC-0001 - Arquitectura hexagonal\n\n- Estado: `proposed`\n- Contexto: Separar dominio de infraestructura.\n- Decision: Usar puertos y adaptadores.\n- Consecuencias: El dominio no puede depender de frameworks.\n",
        "ROADMAP.md": "# ROADMAP.md\n\n## Ahora\n\n- Definir modulos y boundaries.\n\n## Despues\n\n- Implementar casos de uso y adapters.\n",
    }
}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _specnative_root(root: Path) -> Path:
    return root / "spec-native"


def _next_decision_id(existing: str) -> str:
    ids = [int(value) for value in re.findall(r"DEC-(\d+)", existing)]
    return f"DEC-{(max(ids) + 1) if ids else 1:04d}"


def _slug_upper(initiative: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", initiative.upper()).strip("-")[:24] or "NEW"


def _user_spec_templates(root: Path) -> dict[str, str]:
    base = root / ".specnative" / "templates" / "specs"
    if not base.is_dir():
        return {}
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted(base.glob("*.md"))}


def _user_decision_snippets(root: Path) -> dict[str, str]:
    base = root / ".specnative" / "templates" / "decisions"
    if not base.is_dir():
        return {}
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted(base.glob("*.md"))}


def _user_archetypes(root: Path) -> dict[str, dict[str, str]]:
    base = root / ".specnative" / "archetypes"
    archetypes: dict[str, dict[str, str]] = {}
    if not base.is_dir():
        return archetypes
    for directory in sorted(path for path in base.iterdir() if path.is_dir()):
        docs = {path.name: path.read_text(encoding="utf-8") for path in directory.glob("*.md")}
        if docs:
            docs.setdefault("description", f"Local archetype from {directory.relative_to(root)}")
            archetypes[directory.name] = docs
    return archetypes


def _write_or_preview(path: Path, content: str, write: bool, *, force: bool = False) -> dict:
    skipped = path.exists() and path.read_text(encoding="utf-8").strip() and not force
    if write and not skipped:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return {
        "path": str(path),
        "written": write and not skipped,
        "skipped": skipped,
        "content": None if write else content.rstrip() + "\n",
    }


def run(
    *,
    action: str = "list-templates",
    template_type: str = "",
    template_name: str | None = None,
    snippet_name: str | None = None,
    archetype_name: str | None = None,
    initiative: str | None = None,
    force: bool = False,
    write: bool = False,
    repo: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        root = Path(repo or cwd or ".").resolve()
        if not root.is_dir():
            return ForgeResult.failure(TOOL, [f"Directory not found: {root}"], t.elapsed_ms)

        spec_templates = {**BUILTIN_SPEC_TEMPLATES, **_user_spec_templates(root)}
        decision_snippets = {**BUILTIN_DECISION_SNIPPETS, **_user_decision_snippets(root)}
        archetypes = {**BUILTIN_ARCHETYPES, **_user_archetypes(root)}

        if action == "list-templates":
            data = {}
            if template_type in ("", "spec"):
                data["spec_templates"] = sorted(spec_templates)
            if template_type in ("", "decision"):
                data["decision_snippets"] = sorted(decision_snippets)
            if template_type not in ("", "spec", "decision"):
                return ForgeResult.failure(TOOL, [f"Unknown template_type '{template_type}'"], t.elapsed_ms)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)

        if action == "list-archetypes":
            return ForgeResult.success(TOOL, {
                "archetypes": [
                    {"name": name, "description": docs.get("description", "")}
                    for name, docs in sorted(archetypes.items())
                ]
            }, t.elapsed_ms)

        if action == "read-archetype":
            name = archetype_name or template_name
            if not name or name not in archetypes:
                return ForgeResult.failure(TOOL, [f"Unknown archetype '{name}'"], t.elapsed_ms, suggestion=f"Valid: {', '.join(sorted(archetypes))}")
            return ForgeResult.success(TOOL, {"name": name, "documents": archetypes[name]}, t.elapsed_ms)

        if action == "apply-archetype":
            name = archetype_name or template_name
            if not name or name not in archetypes:
                return ForgeResult.failure(TOOL, [f"Unknown archetype '{name}'"], t.elapsed_ms, suggestion=f"Valid: {', '.join(sorted(archetypes))}")
            results = []
            for filename, content in archetypes[name].items():
                if filename == "description":
                    continue
                results.append(_write_or_preview(_specnative_root(root) / filename, content, write, force=force))
            return ForgeResult.success(TOOL, {"action": action, "archetype": name, "write": write, "results": results}, t.elapsed_ms)

        if action == "apply-spec-template":
            if not template_name or not initiative:
                return ForgeResult.failure(TOOL, ["--template-name and --initiative are required"], t.elapsed_ms)
            template = spec_templates.get(template_name)
            if template is None:
                return ForgeResult.failure(TOOL, [f"Unknown spec template '{template_name}'"], t.elapsed_ms, suggestion=f"Valid: {', '.join(sorted(spec_templates))}")
            content = template.format(initiative=initiative, slug_upper=_slug_upper(initiative), today=_today())
            path = _specnative_root(root) / "specs" / initiative / "SPEC.md"
            result = _write_or_preview(path, content, write, force=force)
            return ForgeResult.success(TOOL, {"action": action, "template": template_name, "initiative": initiative, **result}, t.elapsed_ms)

        if action == "apply-decision-snippet":
            name = snippet_name or template_name
            if not name:
                return ForgeResult.failure(TOOL, ["--snippet-name is required"], t.elapsed_ms)
            snippet = decision_snippets.get(name)
            if snippet is None:
                return ForgeResult.failure(TOOL, [f"Unknown decision snippet '{name}'"], t.elapsed_ms, suggestion=f"Valid: {', '.join(sorted(decision_snippets))}")
            path = _specnative_root(root) / "DECISIONS.md"
            existing = path.read_text(encoding="utf-8") if path.exists() else "# DECISIONS.md\n"
            content = existing.rstrip() + "\n\n" + snippet.format(dec_id=_next_decision_id(existing), today=_today()).rstrip() + "\n"
            result = _write_or_preview(path, content, write, force=True)
            return ForgeResult.success(TOOL, {"action": action, "snippet": name, **result}, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: list-templates | list-archetypes | read-archetype | apply-archetype | apply-spec-template | apply-decision-snippet"],
            t.elapsed_ms,
        )


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="list-templates", choices=[
        "list-templates", "list-archetypes", "read-archetype", "apply-archetype",
        "apply-spec-template", "apply-decision-snippet",
    ])
    p.add_argument("--template-type", default="")
    p.add_argument("--template-name", default=None)
    p.add_argument("--snippet-name", default=None)
    p.add_argument("--archetype-name", default=None)
    p.add_argument("--initiative", default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--write", action="store_true")
    p.add_argument("--repo", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "SpecNative archetypes, spec templates, and decision snippets", run, _add_args)
