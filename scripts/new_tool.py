#!/usr/bin/env python3
"""
new_tool.py — Generador de scripts para forgetools.

Uso:
    python3 scripts/new_tool.py --category git --name bisect \
        --description "Automated git bisect to find regressions" \
        --command "git bisect" \
        --params "bad:str:HEAD good:str:HEAD~10 script:str|None:None"

    python3 scripts/new_tool.py --interactive

Qué hace:
    1. Crea forgetools/<category>/<name>.py con el patrón ForgeResult completo
    2. Crea forgetools/<category>/__init__.py si no existe
    3. Registra el tool en forgetools/_forge_cli.py
    4. Imprime los próximos pasos

Formato de --params:
    nombre:tipo:default  (separados por espacios)
    Ejemplos:
        path:str:.
        limit:int:100
        recursive:bool:False
        table:str|None:None
        action:str:list   (para enums, documentar en description)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ── Rutas del proyecto ────────────────────────────────────────────────────────

REPO_ROOT   = Path(__file__).parent.parent
FORGE_DIR   = REPO_ROOT / "forgetools"
CLI_FILE    = FORGE_DIR / "_forge_cli.py"

# ── Colores ───────────────────────────────────────────────────────────────────

GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg: str)   -> None: print(f"{GREEN}✓{RESET} {msg}")
def warn(msg: str) -> None: print(f"{YELLOW}⚠{RESET}  {msg}")
def err(msg: str)  -> None: print(f"{RED}✗{RESET} {msg}", file=sys.stderr)
def info(msg: str) -> None: print(f"{CYAN}→{RESET} {msg}")


# ── Parsing de parámetros ─────────────────────────────────────────────────────

def _python_default(raw: str) -> str:
    """Convierte el default en string Python válido."""
    if raw == "None":
        return "None"
    if raw in ("True", "False"):
        return raw
    # número
    try:
        int(raw)
        return raw
    except ValueError:
        pass
    try:
        float(raw)
        return raw
    except ValueError:
        pass
    # string
    return f'"{raw}"'


def parse_params(raw: str) -> list[dict]:
    """
    Parsea 'name:type:default name2:type2:default2 ...'
    Retorna lista de dicts con keys: name, type, default, default_py
    """
    params = []
    for token in raw.strip().split():
        parts = token.split(":")
        if len(parts) != 3:
            err(f"Parámetro inválido: '{token}' — formato esperado: nombre:tipo:default")
            sys.exit(1)
        name, typ, default = parts
        params.append({
            "name":       name,
            "type":       typ,
            "default":    default,
            "default_py": _python_default(default),
        })
    return params


# ── Generación del archivo ────────────────────────────────────────────────────

def _run_signature(params: list[dict]) -> str:
    """Genera la firma de run() con keyword-only args."""
    if not params:
        return "def run(*, cwd: str | None = None) -> ForgeResult:"
    args = ["*"]
    for p in params:
        args.append(f"{p['name']}: {p['type']} = {p['default_py']}")
    args.append("cwd: str | None = None")
    inner = ", ".join(args)
    return f"def run({inner}) -> ForgeResult:"


def _add_args_body(params: list[dict]) -> str:
    """Genera el cuerpo de _add_args()."""
    if not params:
        return "    pass"
    lines = []
    for p in params:
        name_flag = p["name"].replace("_", "-")
        typ = p["type"].replace("str | None", "str").replace("int | None", "int")
        base_type = typ.split("|")[0].strip()
        if base_type == "bool":
            lines.append(
                f'    p.add_argument("--{name_flag}", action="store_true", '
                f'dest="{p["name"]}", help="{p["name"]}")'
            )
        else:
            lines.append(
                f'    p.add_argument("--{name_flag}", default={p["default_py"]}, '
                f'type={base_type}, dest="{p["name"]}", help="{p["name"]}")'
            )
    return "\n".join(lines)


def _run_call_args(params: list[dict]) -> str:
    """Genera los args para llamar a run() desde make_cli."""
    if not params:
        return ""
    return ", ".join(f"{p['name']}=args.{p['name']}" for p in params)


def generate_tool_file(
    category: str,
    name: str,
    description: str,
    command: str,
    params: list[dict],
) -> str:
    """Genera el contenido completo del archivo .py."""

    tool_key    = f"{category}.{name.replace('-', '_')}"
    cmd_parts   = command.strip().split()
    cmd_repr    = repr(cmd_parts)
    run_sig     = _run_signature(params)
    add_args    = _add_args_body(params)
    run_call    = _run_call_args(params)

    # Args para pasar al comando (placeholder — el dev los adapta)
    param_comment = ""
    if params:
        param_names = [p["name"] for p in params]
        param_comment = f"    # TODO: build cmd with params: {', '.join(param_names)}\n"

    indent = "        "  # 8 spaces inside with Timer() as t:
    param_comment_indented = f"{indent}# TODO: build cmd with params: {', '.join(p['name'] for p in params)}\n" if params else ""

    return f'''\
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "{tool_key}"


{run_sig}
    with Timer() as t:
{param_comment_indented}\
        cmd = {cmd_repr}
        rc, stdout, stderr = run_command(cmd, cwd=cwd)
        if rc != 0:
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"Command exited with code {{rc}}"],
                t.elapsed_ms,
                suggestion="Check that the required tool is installed and accessible",
            )
        return ForgeResult.success(TOOL, _parse(stdout), t.elapsed_ms)


def _parse(output: str) -> dict:
    """TODO: parse command output into structured dict."""
    lines = [l for l in output.splitlines() if l.strip()]
    return {{"raw": output[:4096], "lines": lines, "count": len(lines)}}


def _add_args(p: argparse.ArgumentParser) -> None:
{add_args}
    p.add_argument("--cwd", default=None, help="Working directory")


if __name__ == "__main__":
    make_cli(TOOL, "{description}", run, _add_args)
'''


# ── Registro en _forge_cli.py ─────────────────────────────────────────────────

def _registry_key(category: str, name: str) -> str:
    return f"{category} {name.replace('_', '-')}"


def _module_path(category: str, name: str) -> str:
    return f"forgetools.{category}.{name.replace('-', '_')}"


def register_in_cli(category: str, name: str) -> bool:
    """Agrega la entrada al REGISTRY en _forge_cli.py. Retorna True si ya existía."""
    content = CLI_FILE.read_text(encoding="utf-8")
    key     = _registry_key(category, name)
    mod     = _module_path(category, name)
    entry   = f'    "{key}": "{mod}",'

    if key in content:
        warn(f'"{key}" ya está registrado en _forge_cli.py — no se modificó')
        return True

    # Buscar el comentario de la categoría para insertar ahí
    cat_comment = f"    # {category}"
    if cat_comment in content:
        # Insertar después del último entry de esa categoría
        idx = content.rfind(cat_comment)
        # Encontrar el fin del bloque de esa categoría (siguiente comentario o })
        next_block = re.search(r'\n    # |\n\}', content[idx:])
        if next_block:
            insert_at = idx + next_block.start()
            content = content[:insert_at] + "\n" + entry + content[insert_at:]
        else:
            content = content.replace("}", entry + "\n}", 1)
    else:
        # Crear nuevo bloque de categoría antes del cierre del dict
        new_block = f"\n    # {category}\n{entry}\n"
        content = content.replace("\n}", new_block + "}", 1)

    CLI_FILE.write_text(content, encoding="utf-8")
    return False


# ── Interactivo ───────────────────────────────────────────────────────────────

def interactive_mode() -> argparse.Namespace:
    print(f"\n{BOLD}forgetools — Generador de nuevo tool{RESET}\n")

    category    = input("Categoría (ej: git, java, db, fs): ").strip().lower()
    name        = input("Nombre del tool (ej: bisect, find-class): ").strip().lower()
    description = input("Descripción corta: ").strip()
    command     = input("Comando base (ej: git bisect): ").strip()
    params_raw  = input(
        "Parámetros nombre:tipo:default (vacío si ninguno)\n"
        "  Ej: path:str:. limit:int:100 recursive:bool:False\n"
        "  → "
    ).strip()

    ns = argparse.Namespace(
        category=category,
        name=name,
        description=description,
        command=command,
        params=params_raw,
        dry_run=False,
    )
    return ns


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un nuevo script de forgetools con el patrón ForgeResult.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--category",    help="Categoría (git, java, db, fs, …)")
    parser.add_argument("--name",        help="Nombre del tool (bisect, find-class, …)")
    parser.add_argument("--description", help="Descripción corta del tool")
    parser.add_argument("--command",     help='Comando base que wrappea (ej: "git bisect")')
    parser.add_argument("--params",      default="",
                        help="Parámetros: nombre:tipo:default … (separados por espacios)")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Modo interactivo con prompts")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Muestra el archivo generado sin escribirlo")
    args = parser.parse_args()

    # Modo interactivo
    if args.interactive or not args.category:
        args = interactive_mode()

    # Validaciones
    if not args.category or not args.name:
        err("--category y --name son requeridos")
        sys.exit(1)
    if not re.match(r'^[a-z][a-z0-9_-]*$', args.category):
        err(f"Categoría inválida: '{args.category}' — solo minúsculas, guiones y números")
        sys.exit(1)
    if not re.match(r'^[a-z][a-z0-9_-]*$', args.name):
        err(f"Nombre inválido: '{args.name}' — solo minúsculas, guiones y números")
        sys.exit(1)

    category    = args.category
    name        = args.name.replace("-", "_")
    name_dash   = args.name.replace("_", "-")
    description = getattr(args, "description", "") or f"{category} {name} tool"
    command     = getattr(args, "command", "")     or f"{category} {name}"
    params_raw  = getattr(args, "params", "")      or ""
    dry_run     = getattr(args, "dry_run", False)

    params = parse_params(params_raw) if params_raw.strip() else []

    # Paths
    cat_dir   = FORGE_DIR / category
    init_file = cat_dir / "__init__.py"
    tool_file = cat_dir / f"{name}.py"

    # Generar contenido
    content = generate_tool_file(category, name, description, command, params)

    print()
    info(f"Tool: {BOLD}{category} {name_dash}{RESET}")
    info(f"Archivo: forgetools/{category}/{name}.py")
    info(f"Módulo:  forgetools.{category}.{name}")
    info(f"MCP:     {category}_{name}")
    info(f"CLI:     forge {category} {name_dash}")
    print()

    if dry_run:
        print(f"{'─' * 60}")
        print(content)
        print(f"{'─' * 60}")
        info("--dry-run activo: no se escribió ningún archivo")
        return

    # Crear categoría si no existe
    if not cat_dir.exists():
        cat_dir.mkdir(parents=True)
        ok(f"Directorio creado: forgetools/{category}/")

    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")
        ok(f"Creado: forgetools/{category}/__init__.py")

    # Crear tool file
    if tool_file.exists():
        warn(f"Ya existe: forgetools/{category}/{name}.py — se sobreescribirá")
        resp = input("¿Continuar? [s/N] ").strip().lower()
        if resp not in ("s", "si", "sí", "y", "yes"):
            info("Cancelado.")
            return

    tool_file.write_text(content, encoding="utf-8")
    ok(f"Creado: forgetools/{category}/{name}.py")

    # Registrar en _forge_cli.py
    already = register_in_cli(category, name_dash)
    if not already:
        ok(f'Registrado en _forge_cli.py: "{category} {name_dash}"')

    # Próximos pasos
    print()
    print(f"{BOLD}Próximos pasos:{RESET}")
    print(f"  1. Edita forgetools/{category}/{name}.py")
    print(f"     → Implementa _parse() con la lógica real")
    print(f"     → Ajusta el comando en run() con los params correctos")
    print(f"  2. Prueba: python3 -m forgetools.{category}.{name} --help")
    print(f"  3. git add forgetools/{category}/{name}.py forgetools/_forge_cli.py")
    print(f"  4. git commit -m 'feat: add {category}/{name_dash}'")
    print(f"  5. En opencode: toggle MCP off → on")
    print()


if __name__ == "__main__":
    main()
