from __future__ import annotations

"""
java/maven_modules.py — Discover and inspect Maven modules in a directory tree.

Scans a base directory for subdirectories that contain (or nest) a pom.xml.
Returns structured data: artifactId, version, packaging, source file count,
LICENSE presence, and exact pom.xml path for each discovered module.

Actions:
    list    — discover all Maven modules under --dir (default: cwd)
    info    — detailed info for a single module path
    summary — aggregate stats: total modules, packaging breakdown, versions

Discovery strategy (matches the Ether repo double-nesting pattern):
    1. <dir>/<subdir>/pom.xml          — direct module
    2. <dir>/<subdir>/<subdir>/pom.xml — double-nested (ether-x/ether-x/pom.xml)
    3. <dir>/pom.xml                   — root aggregator
"""

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "java.maven_modules"

_NS = {"m": "http://maven.apache.org/POM/4.0.0"}


# ── POM parsing ───────────────────────────────────────────────────────────────

def _text(elem, tag: str, ns: bool = True) -> str | None:
    """Extract direct child text, trying with and without namespace."""
    prefix = "m:" if ns else ""
    child = elem.find(f"{prefix}{tag}", _NS if ns else {})
    if child is None and ns:
        # Retry without namespace (some POMs omit xmlns)
        child = elem.find(tag)
    return child.text.strip() if child is not None and child.text else None


def _parse_pom(pom_path: Path) -> dict:
    """Extract key metadata from a pom.xml, skipping <parent> block."""
    info: dict = {
        "artifact_id": None,
        "group_id":    None,
        "version":     None,
        "packaging":   "jar",
        "name":        None,
        "description": None,
        "pom_path":    str(pom_path),
    }
    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()

        # Strip namespace from tag to detect it
        tag = root.tag
        has_ns = tag.startswith("{")

        def _get(element, *tags: str) -> str | None:
            """Get first direct child matching any tag name (with/without NS)."""
            for t in tags:
                # with namespace
                child = element.find(f"{{http://maven.apache.org/POM/4.0.0}}{t}")
                if child is not None and child.text:
                    return child.text.strip()
                # without namespace
                child = element.find(t)
                if child is not None and child.text:
                    return child.text.strip()
            return None

        # Packaging sits directly under <project>
        info["packaging"] = _get(root, "packaging") or "jar"

        # artifactId / groupId / version: prefer project-level over parent
        # We need to find the *project* values, not the parent ones.
        # Walk direct children and skip <parent>
        project_artifact = None
        project_group    = None
        project_version  = None
        project_name     = None
        project_desc     = None
        parent_version   = None

        for child in root:
            # Normalize tag (remove namespace)
            local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            text  = (child.text or "").strip()

            if local == "parent":
                for pc in child:
                    pl = pc.tag.split("}")[-1] if "}" in pc.tag else pc.tag
                    if pl == "version":
                        parent_version = (pc.text or "").strip()

            elif local == "artifactId" and text:
                project_artifact = text
            elif local == "groupId" and text:
                project_group = text
            elif local == "version" and text:
                project_version = text
            elif local == "name" and text:
                project_name = text
            elif local == "description" and text:
                project_desc = text

        info["artifact_id"] = project_artifact
        info["group_id"]    = project_group
        info["version"]     = project_version or parent_version
        info["name"]        = project_name
        info["description"] = project_desc

        # Count <module> entries (aggregator POMs)
        modules_elem = None
        for child in root:
            local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if local == "modules":
                modules_elem = child
                break
        if modules_elem is not None:
            sub = [c.text.strip() for c in modules_elem if c.text]
            if sub:
                info["submodules"] = sub

    except ET.ParseError as exc:
        info["parse_error"] = str(exc)
    except Exception as exc:
        info["parse_error"] = str(exc)

    return info


def _count_sources(src_dir: Path) -> dict:
    """Count Java source files and test files under a src/ directory."""
    if not src_dir.is_dir():
        return {"java_files": 0, "test_files": 0}
    all_java   = list(src_dir.rglob("*.java"))
    test_files = [f for f in all_java if "/test/" in str(f)]
    return {
        "java_files": len(all_java),
        "test_files": len(test_files),
        "main_files": len(all_java) - len(test_files),
    }


# ── Discovery ─────────────────────────────────────────────────────────────────

def _discover_pom(candidate: Path) -> Path | None:
    """
    Given a candidate directory, find the pom.xml using the two known patterns:
      1. candidate/pom.xml
      2. candidate/<same-name>/pom.xml  (double-nested Ether pattern)
    Returns the pom.xml Path or None.
    """
    direct = candidate / "pom.xml"
    if direct.is_file():
        return direct

    # Double-nested: ether-foo/ether-foo/pom.xml
    nested = candidate / candidate.name / "pom.xml"
    if nested.is_file():
        return nested

    return None


def _build_module_entry(module_dir: Path, pom: Path) -> dict:
    """Build a full info dict for a single Maven module."""
    pom_info  = _parse_pom(pom)
    src_dir   = pom.parent / "src"
    src_info  = _count_sources(src_dir)
    has_license = (module_dir / "LICENSE").is_file() or (pom.parent / "LICENSE").is_file()
    is_nested = pom.parent != module_dir  # double-nested pattern

    return {
        "module_dir":  str(module_dir),
        "pom_path":    str(pom),
        "nested":      is_nested,
        "has_license": has_license,
        **pom_info,
        **src_info,
    }


def _discover_all(base: Path, pattern: str) -> list[dict]:
    """Scan base dir for subdirs matching pattern and find their pom.xml."""
    results = []

    # Check root pom (aggregator)
    root_pom = base / "pom.xml"
    if root_pom.is_file():
        results.append(_build_module_entry(base, root_pom))

    # Scan child dirs matching pattern
    candidates = sorted(
        d for d in base.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    # Apply pattern filter (supports glob wildcards and plain prefix)
    import fnmatch
    if pattern and pattern != "*":
        candidates = [d for d in candidates if fnmatch.fnmatch(d.name, pattern)]

    for candidate in candidates:
        pom = _discover_pom(candidate)
        if pom:
            results.append(_build_module_entry(candidate, pom))

    return results


# ── Actions ───────────────────────────────────────────────────────────────────

def _action_list(base: Path, pattern: str) -> dict:
    modules = _discover_all(base, pattern)
    return {
        "base_dir": str(base),
        "pattern":  pattern,
        "count":    len(modules),
        "modules":  modules,
    }


def _action_info(target: Path) -> dict:
    # target can be a module dir or the pom.xml itself
    if target.is_file() and target.name == "pom.xml":
        pom = target
        module_dir = target.parent
    else:
        pom = _discover_pom(target)
        module_dir = target
        if pom is None:
            raise FileNotFoundError(f"No pom.xml found under {target}")

    return _build_module_entry(module_dir, pom)


def _action_summary(base: Path, pattern: str) -> dict:
    modules = _discover_all(base, pattern)
    from collections import Counter
    packaging_counts: Counter = Counter()
    version_counts:   Counter = Counter()
    total_java = 0
    total_test = 0
    missing_license = []
    missing_artifact = []

    for m in modules:
        packaging_counts[m.get("packaging") or "jar"] += 1
        v = m.get("version")
        if v:
            version_counts[v] += 1
        total_java += m.get("java_files", 0)
        total_test += m.get("test_files", 0)
        if not m.get("has_license"):
            missing_license.append(m.get("artifact_id") or m["module_dir"])
        if not m.get("artifact_id"):
            missing_artifact.append(m["module_dir"])

    return {
        "base_dir":        str(base),
        "total_modules":   len(modules),
        "total_java_files": total_java,
        "total_test_files": total_test,
        "packaging":       dict(packaging_counts),
        "versions":        dict(version_counts),
        "missing_license": missing_license,
        "missing_artifact_id": missing_artifact,
    }


# ── public run() ─────────────────────────────────────────────────────────────

def run(
    *,
    action:  str = "list",
    dir:     str | None = None,
    path:    str | None = None,   # for action=info: module dir or pom.xml
    pattern: str = "*",           # glob filter for subdir names, e.g. "ether-*"
    cwd:     str | None = None,
) -> ForgeResult:
    with Timer() as t:
        base = Path(dir or cwd or ".").resolve()

        if action == "list":
            if not base.is_dir():
                return ForgeResult.failure(TOOL, [f"Directory not found: {base}"], t.elapsed_ms)
            data = _action_list(base, pattern)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)

        if action == "summary":
            if not base.is_dir():
                return ForgeResult.failure(TOOL, [f"Directory not found: {base}"], t.elapsed_ms)
            data = _action_summary(base, pattern)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)

        if action == "info":
            target_str = path or dir or cwd or "."
            target = Path(target_str).resolve()
            if not target.exists():
                return ForgeResult.failure(TOOL, [f"Path not found: {target}"], t.elapsed_ms)
            try:
                data = _action_info(target)
                return ForgeResult.success(TOOL, data, t.elapsed_ms)
            except FileNotFoundError as exc:
                return ForgeResult.failure(
                    TOOL, [str(exc)], t.elapsed_ms,
                    suggestion="Pass the directory that contains pom.xml or the pom.xml path directly",
                )

        return ForgeResult.failure(
            TOOL,
            [f"Unknown action '{action}'. Use: list | info | summary"],
            t.elapsed_ms,
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--action", default="list",
        choices=["list", "info", "summary"],
        help=(
            "list: discover all Maven modules under --dir (default) | "
            "info: detailed data for a single module (use --path) | "
            "summary: aggregate stats across all modules"
        ),
    )
    p.add_argument(
        "--dir", default=None,
        help="Base directory to scan (default: current working directory)",
    )
    p.add_argument(
        "--path", default=None,
        help="Module directory or pom.xml file for action=info",
    )
    p.add_argument(
        "--pattern", default="*",
        help=(
            "Glob filter for first-level subdirectory names "
            "(e.g. 'ether-*' to scan only Ether modules). Default: * (all)"
        ),
    )
    p.add_argument("--cwd", default=None, help="Working directory override")


if __name__ == "__main__":
    make_cli(
        TOOL,
        "Discover and inspect Maven modules in a directory tree",
        run,
        _add_args,
    )
