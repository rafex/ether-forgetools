from __future__ import annotations

"""
security/eslint_security.py — ESLint security plugin analysis for JS/TS.

Runs ESLint and filters results to security-relevant rules from:
  - eslint-plugin-security      (general JS security)
  - @microsoft/eslint-plugin-security
  - eslint-plugin-no-unsanitized (DOM XSS)
  - eslint-plugin-no-secrets    (hardcoded secrets)
  - @eslint-community/eslint-plugin-security
  - Built-in ESLint rules with security implications (eval, no-new-func, etc.)

If none of the security plugins are installed, the tool reports what to
install and still runs ESLint's built-in security-relevant rules.

Actions:
    scan    — run ESLint on a path and return security findings only
    check   — scan and exit non-zero if any HIGH findings exist
    plugins — list which security plugins are installed in the project
    find    — locate eslint binary and config

ESLint binary search order:
  1. ESLINT_PATH env var
  2. ./node_modules/.bin/eslint  (project-local — preferred)
  3. System PATH (eslint, npx eslint)
  4. ~/.local/share/opencode/bin/eslint
  5. /opt/homebrew/bin/eslint

Severity mapping:
  ESLint severity 2 (error)  → HIGH
  ESLint severity 1 (warn)   → MEDIUM
  All others                 → INFO

Ref: https://github.com/eslint-community/eslint-plugin-security
     https://github.com/nicolo-ribaudo/eslint-plugin-no-unsanitized
"""

import argparse
import json
import os
import re
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "security.eslint_security"

# ── Security rule prefixes / names ────────────────────────────────────────────

_SECURITY_RULE_PREFIXES = (
    "security/",
    "no-unsanitized/",
    "no-secrets/",
    "@microsoft/security/",
    "@eslint-community/security/",
)

# Built-in ESLint rules with security implications
_BUILTIN_SECURITY_RULES = {
    "no-eval",
    "no-new-func",
    "no-implied-eval",
    "no-script-url",
    "no-proto",
    "no-caller",
    "no-extend-native",
}

# Known security plugins and their npm package names
_SECURITY_PLUGINS: dict[str, str] = {
    "security":              "eslint-plugin-security",
    "@microsoft/security":   "@microsoft/eslint-plugin-security",
    "no-unsanitized":        "eslint-plugin-no-unsanitized",
    "no-secrets":            "eslint-plugin-no-secrets",
}

# ── Severity helper ───────────────────────────────────────────────────────────

def _severity(eslint_severity: int) -> str:
    return {2: "HIGH", 1: "MEDIUM"}.get(eslint_severity, "INFO")


def _is_security_rule(rule_id: str | None) -> bool:
    if not rule_id:
        return False
    if any(rule_id.startswith(p) for p in _SECURITY_RULE_PREFIXES):
        return True
    return rule_id in _BUILTIN_SECURITY_RULES


# ── Binary search ─────────────────────────────────────────────────────────────

_ESLINT_SEARCH: list[str] = [
    "./node_modules/.bin/eslint",
    "~/.local/share/opencode/node_modules/.bin/eslint",
    "~/.local/share/nvim/mason/bin/eslint",
    "/opt/homebrew/bin/eslint",
    "/usr/local/bin/eslint",
    "/usr/bin/eslint",
]


def _find_eslint(cwd: str | None) -> str | None:
    import shutil

    env = os.environ.get("ESLINT_PATH")
    if env and Path(env).is_file():
        return env

    base = Path(cwd or ".").resolve()

    # Project-local (highest priority)
    local = base / "node_modules" / ".bin" / "eslint"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)

    # System PATH
    found = shutil.which("eslint")
    if found:
        return found

    # Known locations
    for raw in _ESLINT_SEARCH:
        p = Path(raw).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)

    return None


# ── Plugin detection ──────────────────────────────────────────────────────────

def _detect_installed_plugins(base: Path) -> dict[str, bool]:
    """Check which security plugins are installed in node_modules."""
    nm = base / "node_modules"
    result: dict[str, bool] = {}
    for plugin_key, pkg_name in _SECURITY_PLUGINS.items():
        result[pkg_name] = (nm / pkg_name).is_dir()
    return result


def _read_eslint_config(base: Path) -> str | None:
    """Find active ESLint config file."""
    candidates = [
        "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
        ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json", ".eslintrc.yaml",
        ".eslintrc.yml", ".eslintrc",
    ]
    for c in candidates:
        if (base / c).is_file():
            return c
    pkg = base / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text())
            if "eslintConfig" in data:
                return "package.json#eslintConfig"
        except Exception:
            pass
    return None


# ── Output parser ─────────────────────────────────────────────────────────────

def _parse_eslint_output(raw: str, security_only: bool = True) -> list[dict]:
    try:
        results = json.loads(raw)
    except json.JSONDecodeError:
        return []

    findings: list[dict] = []
    for file_result in results:
        fpath = file_result.get("filePath", "")
        for msg in file_result.get("messages", []):
            rule_id = msg.get("ruleId")
            if security_only and not _is_security_rule(rule_id):
                continue
            findings.append({
                "rule":     rule_id or "unknown",
                "severity": _severity(msg.get("severity", 1)),
                "file":     fpath,
                "line":     msg.get("line", 0),
                "column":   msg.get("column", 0),
                "message":  msg.get("message", ""),
                "category": _rule_category(rule_id or ""),
            })

    findings.sort(key=lambda f: {"HIGH": 0, "MEDIUM": 1, "INFO": 2}.get(f["severity"], 3))
    return findings


def _rule_category(rule_id: str) -> str:
    if "sql" in rule_id.lower():            return "SQL Injection"
    if "xss" in rule_id.lower() or "unsanitized" in rule_id.lower(): return "XSS"
    if "eval" in rule_id.lower():           return "Code Injection"
    if "secret" in rule_id.lower() or "password" in rule_id.lower(): return "Secrets"
    if "regex" in rule_id.lower():          return "ReDoS"
    if "csrf" in rule_id.lower():           return "CSRF"
    if "proto" in rule_id.lower() or "injection" in rule_id.lower(): return "Injection"
    if "object-injection" in rule_id.lower(): return "Object Injection"
    if "child-process" in rule_id.lower() or "non-literal-require" in rule_id.lower():
        return "Command Injection"
    if "timing" in rule_id.lower():         return "Timing Attack"
    if "random" in rule_id.lower():         return "Weak Randomness"
    return "Security"


# ── run() ─────────────────────────────────────────────────────────────────────

def run(
    *,
    action:        str = "scan",
    path:          str = ".",
    security_only: bool = True,
    binary:        str | None = None,
    ext:           str = ".js,.jsx,.ts,.tsx,.mjs,.cjs",
    cwd:           str | None = None,
) -> ForgeResult:
    with Timer() as t:
        base = Path(cwd or ".").resolve()
        scan_path = Path(path) if Path(path).is_absolute() else base / path

        # ── plugins ───────────────────────────────────────────────────────
        if action == "plugins":
            installed = _detect_installed_plugins(base)
            config    = _read_eslint_config(base)
            eslint    = binary or _find_eslint(cwd)
            any_security = any(installed.values())

            return ForgeResult.success(TOOL, {
                "eslint":           eslint,
                "eslint_found":     eslint is not None,
                "config_file":      config,
                "plugins":          installed,
                "any_security_plugin": any_security,
                "install_hint": (
                    None if any_security else
                    "Install a security plugin:\n"
                    "  npm install --save-dev eslint-plugin-security\n"
                    "  # Then add to eslint.config.js:\n"
                    "  # import security from 'eslint-plugin-security'\n"
                    "  # export default [security.configs.recommended]"
                ),
            }, t.elapsed_ms)

        # ── find ──────────────────────────────────────────────────────────
        if action == "find":
            eslint  = binary or _find_eslint(cwd)
            config  = _read_eslint_config(base)
            plugins = _detect_installed_plugins(base)
            return ForgeResult.success(TOOL, {
                "eslint":        eslint,
                "eslint_found":  eslint is not None,
                "config_file":   config,
                "plugins":       plugins,
                "scan_path":     str(scan_path),
            }, t.elapsed_ms)

        # ── scan / check ──────────────────────────────────────────────────
        if action not in ("scan", "check"):
            return ForgeResult.failure(
                TOOL,
                [f"Unknown action '{action}'. Use: scan | check | plugins | find"],
                t.elapsed_ms,
            )

        eslint = binary or _find_eslint(cwd)
        if not eslint:
            return ForgeResult.failure(
                TOOL, ["ESLint not found"],
                t.elapsed_ms,
                suggestion=(
                    "Install locally: npm install --save-dev eslint eslint-plugin-security\n"
                    "Or globally:     npm install -g eslint\n"
                    "Or set:          export ESLINT_PATH=/path/to/eslint"
                ),
            )

        extensions = [e.strip() for e in ext.split(",")]

        cmd = [
            eslint,
            "--format", "json",
            "--no-error-on-unmatched-pattern",
        ]
        # Add extension filters
        for e in extensions:
            cmd += ["--ext", e] if not e.startswith(".") else ["--ext", e]

        cmd.append(str(scan_path))

        rc, stdout, stderr = run_command(cmd, cwd=str(base), timeout=120)

        # ESLint exits 1 when there are linting errors — that's normal
        if rc not in (0, 1) or not stdout.strip():
            return ForgeResult.failure(
                TOOL,
                [stderr.strip() or f"ESLint exited with code {rc}"],
                t.elapsed_ms,
                suggestion=(
                    "Ensure ESLint config exists (.eslintrc.js / eslint.config.js)\n"
                    "and that the scan path contains JS/TS files"
                ),
            )

        findings = _parse_eslint_output(stdout, security_only)
        counts = {"HIGH": 0, "MEDIUM": 0, "INFO": 0}
        for f in findings:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1

        # Group by category for summary
        by_category: dict[str, int] = {}
        for f in findings:
            by_category[f["category"]] = by_category.get(f["category"], 0) + 1

        has_high = counts["HIGH"] > 0
        installed_plugins = _detect_installed_plugins(base)
        any_security_plugin = any(installed_plugins.values())

        data = {
            "eslint":              eslint,
            "scanned":             str(scan_path.relative_to(base)),
            "security_only":       security_only,
            "total":               len(findings),
            "by_severity":         counts,
            "by_category":         by_category,
            "has_high":            has_high,
            "security_plugins":    {k: v for k, v in installed_plugins.items() if v},
            "no_security_plugins": not any_security_plugin,
            "findings":            findings,
            "plugin_hint": (
                None if any_security_plugin else
                "No security plugins detected — only built-in rules checked.\n"
                "Install eslint-plugin-security for comprehensive coverage."
            ),
        }

        if action == "check":
            return ForgeResult(
                ok=not has_high,
                tool=TOOL,
                data=data,
                errors=[f"{counts['HIGH']} HIGH severity security findings"] if has_high else [],
                duration_ms=t.elapsed_ms,
            )

        return ForgeResult.success(TOOL, data, t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="scan",
                   choices=["scan", "check", "plugins", "find"],
                   help=(
                       "scan: run + return security findings (default) | "
                       "check: scan + fail if HIGH findings | "
                       "plugins: list installed security plugins | "
                       "find: locate eslint + config"
                   ))
    p.add_argument("--path", default=".",
                   help="File or directory to scan (default: .)")
    p.add_argument("--all", action="store_false", dest="security_only",
                   help="Include all ESLint findings, not just security rules")
    p.add_argument("--ext", default=".js,.jsx,.ts,.tsx,.mjs,.cjs",
                   help="Comma-separated file extensions (default: .js,.jsx,.ts,.tsx,.mjs,.cjs)")
    p.add_argument("--binary", default=None,
                   help="Override ESLint binary path or set ESLINT_PATH env var")
    p.add_argument("--cwd", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "ESLint security plugin — JS/TS static security analysis", run, _add_args)
