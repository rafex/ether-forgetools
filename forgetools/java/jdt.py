from __future__ import annotations

"""
java/jdt.py — Locator and inspector for eclipse.jdt.ls (Java LSP server).

Does NOT start or communicate with the LSP server — that would require a full
LSP client implementation.  Instead this tool:

  1. Finds the jdtls binary in all known locations (mason, opencode, Homebrew,
     system PATH, JDTLS_PATH env var, custom install dirs).
  2. Reads version info from the install directory (equinox launcher JAR name,
     Cellar path, or mason package metadata).
  3. Detects the correct per-OS config directory (config_mac_arm, config_linux…).
  4. Validates JDK availability and minimum version (17+ required by jdtls 1.x).
  5. Returns a ready-to-use invocation template the agent can embed in
     project-level tooling (launch.json, .nvim.lua, opencode MCP config, etc.)

Actions:
    locate   (default) — find jdtls, report path + version + config dir
    info               — full details: JDK, data dir, plugins, capabilities
    template           — print a ready-to-use CLI invocation template

Ref: https://github.com/eclipse-jdtls/eclipse.jdt.ls
"""

import argparse
import os
import platform
import re
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command

TOOL = "java.jdt"

# ── Binary search order ───────────────────────────────────────────────────────

_BINARY_SEARCH: list[str] = [
    # Environment variable override (highest priority)
    # → handled separately via os.environ
    # opencode managed install
    "~/.local/share/opencode/bin/jdtls/bin/jdtls",
    "~/.local/share/opencode/bin/jdtls",
    # Mason (Neovim)
    "~/.local/share/nvim/mason/bin/jdtls",
    # Homebrew Apple Silicon
    "/opt/homebrew/bin/jdtls",
    # Homebrew Intel
    "/usr/local/bin/jdtls",
    # Linux system
    "/usr/bin/jdtls",
    # Manual installs
    "~/jdtls/bin/jdtls",
    "~/tools/jdtls/bin/jdtls",
    "~/eclipse.jdt.ls/bin/jdtls",
]

# ── Config dir detection ──────────────────────────────────────────────────────

def _config_dir_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        return "config_mac_arm" if machine in ("arm64", "aarch64") else "config_mac"
    if system == "linux":
        return "config_linux_arm" if machine in ("arm64", "aarch64") else "config_linux"
    if system == "windows":
        return "config_win"
    return "config_linux"


# ── Install root from binary path ─────────────────────────────────────────────

def _install_root(binary_path: str) -> Path | None:
    """Given the binary path, try to find the jdtls install root."""
    p = Path(binary_path).resolve()

    # e.g. /opt/homebrew/bin/jdtls → symlink → /opt/homebrew/Cellar/jdtls/1.x/bin/jdtls
    try:
        real = p.resolve()
    except OSError:
        real = p

    # Walk up to find a dir containing 'plugins' and 'config_*'
    for ancestor in [real, *real.parents]:
        if (ancestor / "plugins").is_dir() or (ancestor / "config_mac").is_dir():
            return ancestor
        # One level up might be libexec (Homebrew pattern)
        libexec = ancestor / "libexec"
        if libexec.is_dir() and (libexec / "plugins").is_dir():
            return libexec

    return None


# ── Version extraction ────────────────────────────────────────────────────────

def _version_from_root(install_root: Path) -> str | None:
    """Extract version from launcher JAR name or Cellar directory."""
    # Homebrew Cellar pattern: .../Cellar/jdtls/1.57.0/...
    for part in install_root.parts:
        if re.match(r"^\d+\.\d+\.\d+$", part):
            return part

    # Mason: read package.json
    pkg = install_root / "package.json"
    if not pkg.exists():
        # Look one level up (mason packages/ dir)
        pkg = install_root.parent / "package.json"
    if pkg.exists():
        try:
            import json
            data = json.loads(pkg.read_text())
            return data.get("version") or data.get("name", "").split("@")[-1] or None
        except Exception:
            pass

    # Equinox launcher JAR: org.eclipse.equinox.launcher_1.6.x.jar
    plugins = install_root / "plugins"
    if plugins.is_dir():
        for jar in plugins.glob("org.eclipse.equinox.launcher_*.jar"):
            m = re.search(r"launcher_(\d+\.\d+\.\d+)", jar.name)
            if m:
                return m.group(1)

    return None


def _version_from_cellar_path(binary: str) -> str | None:
    """Extract version from Homebrew Cellar path component."""
    for part in Path(binary).parts:
        if re.match(r"^\d+\.\d+\.\d+$", part):
            return part
    return None


# ── JDK detection ────────────────────────────────────────────────────────────

def _java_info() -> dict:
    import shutil
    java = shutil.which("java")
    if not java:
        return {"found": False, "path": None, "version": None, "ok": False}

    rc, stdout, stderr = run_command(["java", "-version"], cwd=None)
    # java -version writes to stderr
    output = stderr or stdout
    m = re.search(r'version "(\d+)(?:\.(\d+))?', output)
    if m:
        major = int(m.group(1))
        version_str = m.group(0).replace('version "', "")
        return {
            "found":   True,
            "path":    java,
            "version": version_str,
            "major":   major,
            "ok":      major >= 17,
            "warning": None if major >= 17 else f"jdtls requires Java 17+, found Java {major}",
        }
    return {"found": True, "path": java, "version": "unknown", "ok": True}


# ── Plugin listing ────────────────────────────────────────────────────────────

def _key_plugins(install_root: Path) -> list[str]:
    plugins_dir = install_root / "plugins"
    if not plugins_dir.is_dir():
        return []
    key_prefixes = [
        "org.eclipse.jdt.ls.core",
        "org.eclipse.jdt.core",
        "org.eclipse.equinox.launcher_",
        "org.eclipse.lsp4j",
    ]
    result: list[str] = []
    for prefix in key_prefixes:
        matches = sorted(plugins_dir.glob(f"{prefix}*.jar"))
        if matches:
            result.append(matches[-1].name)  # latest version
    return result


# ── Invocation template ───────────────────────────────────────────────────────

def _build_template(binary: str, install_root: Path | None,
                    config_dir: str, data_dir: str) -> dict:
    config_path = str(install_root / config_dir) if install_root else f"<install_root>/{config_dir}"
    launcher_jar = ""
    if install_root:
        plugins = install_root / "plugins"
        launchers = sorted(plugins.glob("org.eclipse.equinox.launcher_*.jar")) if plugins.is_dir() else []
        launcher_jar = str(launchers[-1]) if launchers else "<install_root>/plugins/org.eclipse.equinox.launcher_*.jar"

    cmd = (
        f"jdtls \\\n"
        f"  --data '{data_dir}' \\\n"
        f"  --add-opens=java.base/java.util=ALL-UNNAMED \\\n"
        f"  --add-opens=java.base/java.lang=ALL-UNNAMED"
    )
    return {
        "binary":          binary,
        "config_dir":      config_path,
        "data_dir":        data_dir,
        "launcher_jar":    launcher_jar,
        "invocation":      cmd,
        "opencode_config": {
            "mcpServers": {
                "jdtls": {
                    "command": binary,
                    "args":    ["--data", data_dir],
                }
            }
        },
    }


# ── run() ─────────────────────────────────────────────────────────────────────

def run(
    *,
    action:   str = "locate",
    binary:   str | None = None,
    data_dir: str | None = None,
    cwd:      str | None = None,
) -> ForgeResult:
    with Timer() as t:
        import shutil

        # 1. Find binary
        exe: str | None = binary

        if not exe:
            exe = os.environ.get("JDTLS_PATH")

        if not exe:
            exe = shutil.which("jdtls")

        if not exe:
            for raw in _BINARY_SEARCH:
                p = Path(raw).expanduser()
                if p.is_file() and os.access(p, os.X_OK):
                    exe = str(p)
                    break

        if not exe:
            return ForgeResult.failure(
                TOOL,
                ["jdtls binary not found"],
                t.elapsed_ms,
                suggestion=(
                    "Install via Homebrew:  brew install jdtls\n"
                    "Install via Mason:     :MasonInstall jdtls\n"
                    "Or set env var:        export JDTLS_PATH=/path/to/jdtls"
                ),
            )

        # 2. Resolve install root and version
        install_root   = _install_root(exe)
        version        = (
            _version_from_root(install_root) if install_root
            else _version_from_cellar_path(exe)
        )
        config_dir_name = _config_dir_name()
        config_dir_path = str(install_root / config_dir_name) if install_root else None
        config_exists   = Path(config_dir_path).is_dir() if config_dir_path else False

        resolved_data = data_dir or str(
            Path("~/.cache/jdtls-workspace").expanduser()
        )

        # ── locate (minimal) ──────────────────────────────────────────────
        if action == "locate":
            return ForgeResult.success(TOOL, {
                "found":        True,
                "binary":       exe,
                "version":      version,
                "install_root": str(install_root) if install_root else None,
                "config_dir":   config_dir_path,
                "config_exists": config_exists,
                "data_dir":     resolved_data,
                "os_profile":   config_dir_name,
            }, t.elapsed_ms)

        # ── info (full details) ───────────────────────────────────────────
        if action == "info":
            java = _java_info()
            plugins = _key_plugins(install_root) if install_root else []
            return ForgeResult.success(TOOL, {
                "found":        True,
                "binary":       exe,
                "version":      version,
                "install_root": str(install_root) if install_root else None,
                "config_dir":   config_dir_path,
                "config_exists": config_exists,
                "data_dir":     resolved_data,
                "os_profile":   config_dir_name,
                "java":         java,
                "key_plugins":  plugins,
                "ready":        java.get("ok", False) and config_exists,
                "issues": [
                    *(["Java 17+ required"] if not java.get("ok") else []),
                    *(["Config directory not found"] if not config_exists else []),
                ],
            }, t.elapsed_ms)

        # ── template ──────────────────────────────────────────────────────
        if action == "template":
            tpl = _build_template(exe, install_root, config_dir_name, resolved_data)
            return ForgeResult.success(TOOL, tpl, t.elapsed_ms)

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: locate | info | template"],
            t.elapsed_ms,
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--action", default="locate",
                   choices=["locate", "info", "template"],
                   help=(
                       "locate: find binary + version (default) | "
                       "info: full install details + JDK check | "
                       "template: ready-to-use CLI invocation"
                   ))
    p.add_argument("--binary", default=None,
                   help="Override jdtls binary path (or set JDTLS_PATH env var)")
    p.add_argument("--data-dir", dest="data_dir", default=None,
                   help="jdtls workspace data dir (default: ~/.cache/jdtls-workspace)")
    p.add_argument("--cwd", default=None)


if __name__ == "__main__":
    make_cli(TOOL, "Locate and inspect eclipse.jdt.ls installation", run, _add_args)
