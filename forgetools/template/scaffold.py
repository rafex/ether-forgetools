"""forgetools.template.scaffold — Scaffold files from built-in templates."""
from __future__ import annotations

import argparse
import json
import os

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "template.scaffold"

_TEMPLATES: dict[str, str] = {
    "java-class": (
        "package {package};\n\n"
        "public class {class_name} {{\n\n"
        "    public {class_name}() {{}}\n\n"
        "}}\n"
    ),
    "java-test": (
        "package {package};\n\n"
        "import org.junit.jupiter.api.Test;\n"
        "import static org.junit.jupiter.api.Assertions.*;\n\n"
        "class {class_name}Test {{\n\n"
        "    @Test\n"
        "    void testExample() {{\n"
        "        // TODO\n"
        "    }}\n"
        "}}\n"
    ),
    "python-module": (
        '"""{module_name} module."""\n\n\n'
        "def main() -> None:\n"
        "    pass\n\n\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    ),
    "python-test": (
        "import pytest\n\n\n"
        "def test_{function_name}():\n"
        "    # TODO\n"
        "    assert True\n"
    ),
    "go-main": (
        'package main\n\nimport "fmt"\n\n'
        'func main() {{\n\tfmt.Println("Hello, {name}!")\n}}\n'
    ),
    "go-test": (
        'package {package}\n\nimport "testing"\n\n'
        "func Test{function_name}(t *testing.T) {{\n\t// TODO\n}}\n"
    ),
    "node-handler": (
        "'use strict';\n\n"
        "/**\n * {handler_name} handler\n */\n"
        "module.exports = async (req, res) => {{\n"
        "  res.json({{ ok: true }});\n"
        "}};\n"
    ),
    "rest-handler": (
        "package {package};\n\n"
        "import org.springframework.web.bind.annotation.*;\n\n"
        "@RestController\n"
        '@RequestMapping("/{path}")\n'
        "public class {class_name}Controller {{\n\n"
        "    @GetMapping\n"
        "    public String get() {{\n"
        '        return "ok";\n'
        "    }}\n"
        "}}\n"
    ),
}

_DEFAULTS: dict[str, dict[str, str]] = {
    "java-class": {"package": "com.example", "class_name": "MyClass"},
    "java-test": {"package": "com.example", "class_name": "MyClass"},
    "python-module": {"module_name": "mymodule"},
    "python-test": {"function_name": "my_function"},
    "go-main": {"name": "World"},
    "go-test": {"package": "mypackage", "function_name": "MyFunction"},
    "node-handler": {"handler_name": "myHandler"},
    "rest-handler": {"package": "com.example", "path": "resource", "class_name": "Resource"},
}


def run(
    *,
    template: str,
    output: str,
    vars: str = "{}",
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if template not in _TEMPLATES:
            return ForgeResult.failure(
                TOOL,
                [f"Unknown template: {template!r}. Available: {', '.join(_TEMPLATES)}"],
                t.elapsed_ms,
            )
        try:
            user_vars = json.loads(vars)
        except json.JSONDecodeError as e:
            return ForgeResult.failure(TOOL, [f"Invalid JSON in vars: {e}"], t.elapsed_ms)

        merged = {**_DEFAULTS.get(template, {}), **user_vars}
        try:
            content = _TEMPLATES[template].format(**merged)
        except KeyError as e:
            return ForgeResult.failure(TOOL, [f"Missing template variable: {e}"], t.elapsed_ms)

        try:
            out_path = output if os.path.isabs(output) else os.path.join(cwd or ".", output)
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            bytes_written = len(content.encode("utf-8"))
        except OSError as e:
            return ForgeResult.failure(TOOL, [f"Failed to write file: {e}"], t.elapsed_ms)

        return ForgeResult.success(TOOL, {
            "template": template,
            "output": out_path,
            "vars": merged,
            "bytes_written": bytes_written,
        }, t.elapsed_ms)


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--template", required=True,
                   choices=list(_TEMPLATES),
                   help="Template name to scaffold")
    p.add_argument("--output", required=True, help="Output file path")
    p.add_argument("--vars", default="{}",
                   help='JSON string of template variables, e.g. \'{"class_name":"MyService"}\'')


if __name__ == "__main__":
    make_cli(TOOL, "Scaffold files from built-in templates", run, _add_args)
