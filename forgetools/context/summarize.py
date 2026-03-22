"""forgetools.context.summarize — Detect project type and return a compact summary."""
from __future__ import annotations

import argparse
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "context.summarize"

_SKIP_DIRS = {".git", "node_modules", ".venv", "target", "__pycache__", ".tox", "dist", "build"}


def run(*, path: str = ".", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            base = Path(cwd or ".") / path
            data = _summarize(base)
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)


def _summarize(base: Path) -> dict:
    has_pom = (base / "pom.xml").exists()
    has_gradle = (base / "build.gradle").exists() or (base / "build.gradle.kts").exists()
    has_package_json = (base / "package.json").exists()
    has_go_mod = (base / "go.mod").exists()
    has_cargo = (base / "Cargo.toml").exists()
    has_pyproject = (base / "pyproject.toml").exists()
    has_setup_py = (base / "setup.py").exists()

    detected = []
    if has_pom or has_gradle:
        detected.append("java")
    if has_package_json:
        detected.append("node")
    if has_go_mod:
        detected.append("go")
    if has_cargo:
        detected.append("rust")
    if has_pyproject or has_setup_py:
        detected.append("python")

    language = "unknown"
    framework = None
    build_tool = None
    name = version = description = None
    main_deps: list[str] = []
    test_framework = None

    if len(detected) > 1:
        language = "polyglot"
    elif detected:
        language = detected[0]

    # Parse manifests
    if has_pom:
        build_tool = "maven"
        name, version, description, main_deps, framework, test_framework = _parse_pom(base / "pom.xml")
    elif has_gradle:
        build_tool = "gradle"
        name = _read_text_fragment(base / "build.gradle") or _read_text_fragment(base / "build.gradle.kts")
        framework, test_framework = _detect_gradle_framework(base)

    if has_package_json:
        build_tool = build_tool or "npm"
        n, v, d, deps, fw, tf = _parse_package_json(base / "package.json")
        if language == "node":
            name, version, description, main_deps, framework, test_framework = n, v, d, deps, fw, tf

    if has_go_mod:
        build_tool = build_tool or "go"
        name, version = _parse_go_mod(base / "go.mod")
        test_framework = "go-test"

    if has_cargo:
        build_tool = build_tool or "cargo"
        name, version, description, main_deps = _parse_cargo_toml(base / "Cargo.toml")
        test_framework = "cargo-test"

    if has_pyproject:
        build_tool = build_tool or "pip"
        n, v, d, deps = _parse_pyproject(base / "pyproject.toml")
        if language == "python":
            name, version, description, main_deps = n, v, d, deps
        test_framework = _detect_py_test_framework(base)

    # Count files
    file_counts: dict[str, int] = {}
    total_files = 0
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            total_files += 1
            ext = os.path.splitext(fname)[1].lstrip(".").lower()
            if ext:
                file_counts[ext] = file_counts.get(ext, 0) + 1

    has_docker = (base / "Dockerfile").exists() or (base / "docker-compose.yml").exists() or (base / "docker-compose.yaml").exists()
    has_ci = (
        (base / ".github" / "workflows").exists()
        or (base / ".gitlab-ci.yml").exists()
        or (base / "Jenkinsfile").exists()
        or (base / ".circleci" / "config.yml").exists()
    )
    has_openapi = any(
        (base / f).exists()
        for f in ("openapi.yaml", "openapi.json", "swagger.yaml", "swagger.json",
                  "openapi.yml", "swagger.yml")
    )

    entry_points = _find_entry_points(base, language)

    return {
        "path": str(base),
        "language": language,
        "framework": framework,
        "build_tool": build_tool,
        "name": name,
        "version": version,
        "description": description,
        "main_dependencies": main_deps[:10],
        "test_framework": test_framework,
        "file_counts": {k: v for k, v in sorted(file_counts.items(), key=lambda x: -x[1])[:15]},
        "total_files": total_files,
        "has_docker": has_docker,
        "has_ci": has_ci,
        "has_openapi": has_openapi,
        "entry_points": entry_points[:3],
    }


def _parse_pom(pom: Path) -> tuple:
    try:
        tree = ET.parse(pom)
        root = tree.getroot()
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        def t(tag: str) -> str:
            return f"{ns}{tag}"

        name = (root.findtext(t("artifactId")) or "").strip()
        version = (root.findtext(t("version")) or "").strip()
        description = (root.findtext(t("description")) or "").strip() or None

        deps: list[str] = []
        framework = None
        test_framework = "junit"
        for dep in root.iter(t("dependency")):
            gid = dep.findtext(t("groupId")) or ""
            aid = dep.findtext(t("artifactId")) or ""
            if gid and aid:
                deps.append(f"{gid}:{aid}")
            if "spring-boot" in gid or "spring-boot" in aid:
                framework = "spring-boot"
            if "quarkus" in gid:
                framework = "quarkus"
            if "micronaut" in gid:
                framework = "micronaut"
            if "junit-jupiter" in aid or "junit5" in aid:
                test_framework = "junit5"

        return name or None, version or None, description, deps[:10], framework, test_framework
    except Exception:
        return None, None, None, [], None, "junit"


def _detect_gradle_framework(base: Path) -> tuple:
    framework = None
    test_framework = "junit"
    for fname in ("build.gradle", "build.gradle.kts"):
        fpath = base / fname
        if fpath.exists():
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore").lower()
                if "spring-boot" in text:
                    framework = "spring-boot"
                if "quarkus" in text:
                    framework = "quarkus"
                if "junit5" in text or "junit-jupiter" in text:
                    test_framework = "junit5"
            except OSError:
                pass
    return framework, test_framework


def _parse_package_json(pkg: Path) -> tuple:
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        name = data.get("name")
        version = data.get("version")
        description = data.get("description") or None
        deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
        framework = None
        test_framework = None
        all_deps = set(deps)
        if "react" in all_deps:
            framework = "react"
        elif "express" in all_deps:
            framework = "express"
        elif "next" in all_deps:
            framework = "next"
        elif "vue" in all_deps:
            framework = "vue"
        elif "@angular/core" in all_deps:
            framework = "angular"
        if "jest" in all_deps:
            test_framework = "jest"
        elif "mocha" in all_deps:
            test_framework = "mocha"
        elif "vitest" in all_deps:
            test_framework = "vitest"
        return name, version, description, list(data.get("dependencies", {}).keys())[:10], framework, test_framework
    except Exception:
        return None, None, None, [], None, None


def _parse_go_mod(gomod: Path) -> tuple:
    try:
        for line in gomod.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("module "):
                module = line.split()[1]
                return module, None
    except OSError:
        pass
    return None, None


def _parse_cargo_toml(cargo: Path) -> tuple:
    try:
        text = cargo.read_text(encoding="utf-8")
        name = version = description = None
        deps: list[str] = []
        in_package = in_deps = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "[package]":
                in_package = True
                in_deps = False
            elif stripped == "[dependencies]" or stripped.startswith("[dependencies."):
                in_deps = True
                in_package = False
            elif stripped.startswith("["):
                in_package = in_deps = False
            elif in_package:
                if stripped.startswith("name"):
                    name = stripped.split("=", 1)[1].strip().strip('"\'')
                elif stripped.startswith("version"):
                    version = stripped.split("=", 1)[1].strip().strip('"\'')
                elif stripped.startswith("description"):
                    description = stripped.split("=", 1)[1].strip().strip('"\'')
            elif in_deps and "=" in stripped:
                dep_name = stripped.split("=")[0].strip()
                if dep_name and not dep_name.startswith("#"):
                    deps.append(dep_name)
        return name, version, description, deps[:10]
    except Exception:
        return None, None, None, []


def _parse_pyproject(pyproject: Path) -> tuple:
    try:
        text = pyproject.read_text(encoding="utf-8")
        name = version = description = None
        deps: list[str] = []
        in_project = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "[project]" or stripped == "[tool.poetry]":
                in_project = True
            elif stripped.startswith("[") and stripped != "[project]":
                in_project = False
            elif in_project:
                if stripped.startswith("name"):
                    name = stripped.split("=", 1)[1].strip().strip('"\'')
                elif stripped.startswith("version"):
                    version = stripped.split("=", 1)[1].strip().strip('"\'')
                elif stripped.startswith("description"):
                    description = stripped.split("=", 1)[1].strip().strip('"\'')
                elif stripped.startswith('"') and stripped.endswith('"'):
                    dep = stripped.strip('"').split(">=")[0].split("==")[0].strip()
                    if dep:
                        deps.append(dep)
        return name, version, description, deps[:10]
    except Exception:
        return None, None, None, []


def _detect_py_test_framework(base: Path) -> str | None:
    for fname in ("pyproject.toml", "setup.cfg", "pytest.ini", "tox.ini"):
        if (base / fname).exists():
            return "pytest"
    if (base / "tests").is_dir() or (base / "test").is_dir():
        return "pytest"
    return None


def _read_text_fragment(p: Path) -> str | None:
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8", errors="ignore")[:200]
    except OSError:
        return None


def _find_entry_points(base: Path, language: str) -> list[str]:
    candidates = []
    patterns = {
        "java": ["src/main/java/**/*Application.java", "src/main/java/**/Main.java"],
        "node": ["src/index.js", "index.js", "src/app.js", "app.js", "src/server.js"],
        "go": ["main.go", "cmd/*/main.go"],
        "rust": ["src/main.rs"],
        "python": ["main.py", "app.py", "run.py", "__main__.py"],
    }
    import glob
    for pattern in patterns.get(language, []):
        matches = glob.glob(str(base / pattern), recursive=True)
        candidates.extend(matches)
    return [os.path.relpath(c, base) for c in candidates[:3]]


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".", help="Path to the project directory")


if __name__ == "__main__":
    make_cli(TOOL, "Detect project type and return a compact summary", run, _add_args)
