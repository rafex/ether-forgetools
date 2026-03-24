"""
Validate config files: JSON, YAML, TOML, XML, Properties, .env, INI.
Auto-detects format from extension. Reports all errors, not just the first.
"""
from __future__ import annotations

import argparse
import configparser
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "config.validate"

# Formats detectable from extension
_EXT_MAP: dict[str, str] = {
    ".json":       "json",
    ".yaml":       "yaml",
    ".yml":        "yaml",
    ".toml":       "toml",
    ".xml":        "xml",
    ".properties": "properties",
    ".env":        "env",
    ".ini":        "ini",
    ".cfg":        "ini",
    ".conf":       "ini",
}

SUPPORTED = sorted(set(_EXT_MAP.values()))


# ── validators ────────────────────────────────────────────────────────────────

def _validate_json(text: str) -> list[str]:
    try:
        json.loads(text)
        return []
    except json.JSONDecodeError as e:
        return [f"line {e.lineno}, col {e.colno}: {e.msg}"]


def _validate_yaml(text: str) -> list[str]:
    try:
        import yaml  # PyYAML — optional
        list(yaml.safe_load_all(text))
        return []
    except ImportError:
        return ["PyYAML not installed — run: pip install pyyaml"]
    except Exception as e:
        return [str(e)]


def _validate_toml(text: str) -> list[str]:
    try:
        import tomllib  # stdlib Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # fallback
        except ImportError:
            return ["tomllib not available (Python < 3.11) — run: pip install tomli"]
    try:
        tomllib.loads(text)
        return []
    except Exception as e:
        return [str(e)]


def _validate_xml(text: str) -> list[str]:
    errors: list[str] = []
    try:
        ET.fromstring(text)
    except ET.ParseError as e:
        errors.append(str(e))
    # Extra: check unclosed tags heuristic
    open_tags = re.findall(r"<([a-zA-Z_][\w.-]*)[\s>]", text)
    close_tags = re.findall(r"</([a-zA-Z_][\w.-]*)>", text)
    selfclose = re.findall(r"<([a-zA-Z_][\w.-][^>]*)/>", text)
    return errors


def _validate_properties(text: str) -> list[str]:
    errors: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue
        # Key must be present; value after = or : is optional
        if not re.match(r"^[^\s=:]+\s*[=:]", stripped) and "=" not in stripped and ":" not in stripped:
            errors.append(f"line {i}: no key=value separator found: {stripped!r}")
    return errors


def _validate_env(text: str) -> list[str]:
    errors: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # export KEY=VALUE or KEY=VALUE
        clean = re.sub(r"^export\s+", "", stripped)
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", clean):
            errors.append(f"line {i}: invalid env entry: {stripped!r}")
    return errors


def _validate_ini(text: str) -> list[str]:
    parser = configparser.RawConfigParser()
    try:
        parser.read_string(text)
        return []
    except configparser.Error as e:
        return [str(e)]


_VALIDATORS = {
    "json":       _validate_json,
    "yaml":       _validate_yaml,
    "toml":       _validate_toml,
    "xml":        _validate_xml,
    "properties": _validate_properties,
    "env":        _validate_env,
    "ini":        _validate_ini,
}


# ── public API ────────────────────────────────────────────────────────────────

def run(
    *,
    file: str,
    fmt: str | None = None,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        path = Path(file) if os.path.isabs(file) else Path(cwd or ".") / file

        if not path.exists():
            return ForgeResult.failure(
                TOOL,
                [f"File not found: {path}"],
                t.elapsed_ms,
                suggestion="Check the path or run from the project root",
            )

        # Detect format
        detected_fmt = fmt or _EXT_MAP.get(path.suffix.lower())
        if not detected_fmt:
            return ForgeResult.failure(
                TOOL,
                [f"Cannot detect format for extension '{path.suffix}'. Use --fmt to specify."],
                t.elapsed_ms,
                suggestion=f"Supported formats: {', '.join(SUPPORTED)}",
            )

        if detected_fmt not in _VALIDATORS:
            return ForgeResult.failure(
                TOOL,
                [f"Unsupported format: {detected_fmt}"],
                t.elapsed_ms,
                suggestion=f"Supported: {', '.join(SUPPORTED)}",
            )

        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            return ForgeResult.failure(TOOL, [f"Cannot read file: {e}"], t.elapsed_ms)

        errors = _VALIDATORS[detected_fmt](text)

        data: dict[str, Any] = {
            "file":   str(path),
            "format": detected_fmt,
            "valid":  len(errors) == 0,
            "errors": errors,
            "lines":  text.count("\n") + 1,
            "size_bytes": len(text.encode()),
        }

        if errors:
            return ForgeResult(
                ok=False,
                tool=TOOL,
                data=data,
                errors=errors,
                duration_ms=t.elapsed_ms,
                suggestion=f"Fix the {len(errors)} error(s) listed in data.errors",
            )

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("file", help="File to validate")
    p.add_argument(
        "--fmt",
        choices=SUPPORTED,
        default=None,
        help="Force format (auto-detected from extension if omitted)",
    )


if __name__ == "__main__":
    make_cli(TOOL, "Validate config files (JSON, YAML, TOML, XML, Properties, .env, INI)", run, _add_args)
