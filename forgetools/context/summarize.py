"""forgetools.context.summarize — 7-block project summary for code agents.

Block 1 — structure    : top-level dirs (maxdepth 2)
Block 2 — languages    : detected langs + file counts
Block 3 — build/deps   : build tool, framework, deps, maven modules
Block 4 — entry points : main() files with smart Java preview (skips header/javadoc)
Block 5 — key modules  : controller/service/repo files with class-level preview
Block 6 — config       : docker, ci, .env, lint, openapi, .github/workflows
Block 7 — git state    : branch, log, status, worktrees, submodules
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "context.summarize"

_SKIP_DIRS: set[str] = {
    ".git", "node_modules", ".venv", "venv", "target", "__pycache__",
    ".tox", "dist", "build", ".next", ".nuxt", ".mvn", ".cache",
    "vendor", ".eggs", "coverage", "out",
}

# regex to find the first real Java type declaration (skips license + javadoc)
_JAVA_TYPE_RE = re.compile(
    r"^\s*(?:(?:public|protected|private)\s+)?(?:(?:abstract|final|sealed)\s+)?"
    r"(?:class|interface|enum|record|@interface)\s+\w+"
)


# ── Bloque 1: estructura ──────────────────────────────────────────────────────

def _block_structure(base: Path) -> dict:
    top = sorted(
        p.name for p in base.iterdir()
        if p.is_dir() and p.name not in _SKIP_DIRS and not p.name.startswith(".")
    )
    depth2: list[str] = []
    for d in top:
        sub = base / d
        try:
            children = sorted(
                f"{d}/{p.name}" for p in sub.iterdir()
                if p.is_dir() and p.name not in _SKIP_DIRS and not p.name.startswith(".")
            )
            depth2.extend(children[:6])
        except PermissionError:
            pass

    return {"top_level_dirs": top, "depth_2_dirs": depth2[:30]}


# ── Bloque 2: lenguajes ───────────────────────────────────────────────────────

_LANG_EXTS: dict[str, list[str]] = {
    "java":       [".java"],
    "kotlin":     [".kt", ".kts"],
    "javascript": [".js", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "python":     [".py"],
    "go":         [".go"],
    "rust":       [".rs"],
    "php":        [".php"],
    "ruby":       [".rb"],
    "shell":      [".sh", ".bash", ".zsh"],
    "yaml":       [".yml", ".yaml"],
    "xml":        [".xml"],
    "json":       [".json"],
    "sql":        [".sql"],
    "markdown":   [".md", ".mdx"],
}
_EXT_TO_LANG: dict[str, str] = {
    ext: lang for lang, exts in _LANG_EXTS.items() for ext in exts
}


def _block_languages(base: Path) -> dict:
    counts: dict[str, int] = {}
    total = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fname in filenames:
            total += 1
            ext = os.path.splitext(fname)[1].lower()
            lang = _EXT_TO_LANG.get(ext, "other")
            counts[lang] = counts.get(lang, 0) + 1

    sorted_counts = dict(sorted(counts.items(), key=lambda x: -x[1])[:12])
    detected = [
        lang for lang in ["java", "kotlin", "typescript", "javascript",
                          "python", "go", "rust", "php", "ruby"]
        if counts.get(lang, 0) > 0
    ]
    primary = detected[0] if detected else (list(sorted_counts.keys())[0] if sorted_counts else "unknown")
    return {
        "primary": primary,
        "detected": detected,
        "file_counts": sorted_counts,
        "total_files": total,
    }


# ── Bloque 3: build y dependencias ───────────────────────────────────────────

def _block_build(base: Path) -> dict:
    result: dict = {
        "build_tool": None, "framework": None, "test_framework": None,
        "name": None, "version": None, "description": None,
        "main_dependencies": [], "maven_modules": [],
    }

    # Maven
    pom = base / "pom.xml"
    if pom.exists():
        result["build_tool"] = "maven"
        name, version, desc, deps, fw, tf, modules = _parse_pom(pom)
        result.update(name=name, version=version, description=desc,
                      main_dependencies=deps, framework=fw,
                      test_framework=tf, maven_modules=modules)

    # Gradle
    for gf in ("build.gradle", "build.gradle.kts"):
        if (base / gf).exists():
            result["build_tool"] = result["build_tool"] or "gradle"
            fw, tf = _detect_gradle_framework(base)
            result["framework"] = result["framework"] or fw
            result["test_framework"] = result["test_framework"] or tf
            break

    # Node
    pkg = base / "package.json"
    if pkg.exists():
        result["build_tool"] = result["build_tool"] or "npm"
        n, v, d, deps, fw, tf = _parse_package_json(pkg)
        if result["name"] is None:
            result.update(name=n, version=v, description=d,
                          main_dependencies=deps, framework=fw, test_framework=tf)

    # Go
    if (base / "go.mod").exists():
        result["build_tool"] = result["build_tool"] or "go"
        n, v = _parse_go_mod(base / "go.mod")
        result["name"] = result["name"] or n
        result["test_framework"] = result["test_framework"] or "go-test"

    # Rust
    if (base / "Cargo.toml").exists():
        result["build_tool"] = result["build_tool"] or "cargo"
        n, v, d, deps = _parse_cargo_toml(base / "Cargo.toml")
        if result["name"] is None:
            result.update(name=n, version=v, description=d, main_dependencies=deps)
        result["test_framework"] = result["test_framework"] or "cargo-test"

    # Python
    if (base / "pyproject.toml").exists():
        result["build_tool"] = result["build_tool"] or "pip"
        n, v, d, deps = _parse_pyproject(base / "pyproject.toml")
        if result["name"] is None:
            result.update(name=n, version=v, description=d, main_dependencies=deps)
        result["test_framework"] = result["test_framework"] or _detect_py_test_framework(base)

    return result


def _parse_pom(pom: Path) -> tuple:
    try:
        tree = ET.parse(pom)
        root = tree.getroot()
        ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""

        def t(tag: str) -> str:
            return f"{ns}{tag}"

        name = (root.findtext(t("artifactId")) or "").strip() or None
        version = (root.findtext(t("version")) or "").strip() or None
        description = (root.findtext(t("description")) or "").strip() or None
        modules = [m.text.strip() for m in root.iter(t("module")) if m.text]

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
            elif "quarkus" in gid:
                framework = "quarkus"
            elif "micronaut" in gid:
                framework = "micronaut"
            if "junit-jupiter" in aid or "junit5" in aid:
                test_framework = "junit5"

        return name, version, description, deps[:12], framework, test_framework, modules
    except Exception:
        return None, None, None, [], None, "junit", []


def _detect_gradle_framework(base: Path) -> tuple:
    framework = None
    test_framework = "junit"
    for fname in ("build.gradle", "build.gradle.kts"):
        fp = base / fname
        if fp.exists():
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore").lower()
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
        deps_all = set(data.get("dependencies", {}).keys()) | set(data.get("devDependencies", {}).keys())
        fw = (
            "react" if "react" in deps_all else
            "next" if "next" in deps_all else
            "vue" if "vue" in deps_all else
            "angular" if "@angular/core" in deps_all else
            "express" if "express" in deps_all else None
        )
        tf = (
            "jest" if "jest" in deps_all else
            "vitest" if "vitest" in deps_all else
            "mocha" if "mocha" in deps_all else None
        )
        return (data.get("name"), data.get("version"), data.get("description") or None,
                list(data.get("dependencies", {}).keys())[:10], fw, tf)
    except Exception:
        return None, None, None, [], None, None


def _parse_go_mod(gomod: Path) -> tuple:
    try:
        for line in gomod.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("module "):
                return line.strip().split()[1], None
    except OSError:
        pass
    return None, None


def _parse_cargo_toml(cargo: Path) -> tuple:
    name = version = description = None
    deps: list[str] = []
    in_pkg = in_dep = False
    try:
        for line in cargo.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s == "[package]":
                in_pkg, in_dep = True, False
            elif s in ("[dependencies]", "[dev-dependencies]") or s.startswith("[dependencies."):
                in_dep, in_pkg = True, False
            elif s.startswith("["):
                in_pkg = in_dep = False
            elif in_pkg:
                if s.startswith("name"):
                    name = s.split("=", 1)[1].strip().strip("\"'")
                elif s.startswith("version"):
                    version = s.split("=", 1)[1].strip().strip("\"'")
                elif s.startswith("description"):
                    description = s.split("=", 1)[1].strip().strip("\"'")
            elif in_dep and "=" in s and not s.startswith("#"):
                deps.append(s.split("=")[0].strip())
    except OSError:
        pass
    return name, version, description, deps[:10]


def _parse_pyproject(pyproject: Path) -> tuple:
    name = version = description = None
    deps: list[str] = []
    in_proj = False
    try:
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s in ("[project]", "[tool.poetry]"):
                in_proj = True
            elif s.startswith("["):
                in_proj = False
            elif in_proj:
                if s.startswith("name"):
                    name = s.split("=", 1)[1].strip().strip("\"'")
                elif s.startswith("version"):
                    version = s.split("=", 1)[1].strip().strip("\"'")
                elif s.startswith("description"):
                    description = s.split("=", 1)[1].strip().strip("\"'")
                elif s.startswith('"') and s.endswith('"'):
                    dep = s.strip('"').split(">=")[0].split("==")[0].split("[")[0].strip()
                    if dep:
                        deps.append(dep)
    except OSError:
        pass
    return name, version, description, deps[:10]


def _detect_py_test_framework(base: Path) -> str | None:
    for f in ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"):
        if (base / f).exists():
            return "pytest"
    return "pytest" if ((base / "tests").is_dir() or (base / "test").is_dir()) else None


# ── Bloque 4: entry points con preview inteligente ───────────────────────────

def _java_class_preview(path: Path, lines: int = 40) -> str:
    """Skip license header + javadoc, return N lines starting from the type declaration."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, line in enumerate(text):
            if _JAVA_TYPE_RE.search(line):
                return "\n".join(text[i: i + lines])
        # fallback: first non-blank, non-comment line
        for i, line in enumerate(text):
            stripped = line.strip()
            if stripped and not stripped.startswith("//") and not stripped.startswith("*") and not stripped.startswith("/*"):
                return "\n".join(text[i: i + lines])
    except OSError:
        pass
    return ""


def _block_entry_points(base: Path, primary_lang: str) -> dict:
    patterns: dict[str, list[str]] = {
        "java":   ["**/src/main/java/**/*Application.java",
                   "**/src/main/java/**/Main.java",
                   "**/src/main/java/**/*Main.java"],
        "kotlin": ["**/src/main/kotlin/**/*Application.kt",
                   "**/src/main/kotlin/**/Main.kt"],
        "node":   ["src/index.js", "index.js", "src/app.js",
                   "app.js", "src/server.js", "src/main.ts", "src/index.ts"],
        "go":     ["main.go", "cmd/*/main.go", "cmd/**/main.go"],
        "rust":   ["src/main.rs"],
        "python": ["main.py", "app.py", "run.py", "__main__.py", "manage.py"],
    }
    found: list[dict] = []
    for pattern in patterns.get(primary_lang, []):
        for match in glob.glob(str(base / pattern), recursive=True)[:2]:
            rel = os.path.relpath(match, base)
            preview = (
                _java_class_preview(Path(match))
                if primary_lang in ("java", "kotlin")
                else _generic_preview(Path(match))
            )
            found.append({"path": rel, "preview": preview})
            if len(found) >= 3:
                break
        if len(found) >= 3:
            break

    # Also grep for public static void main across Java files if none found
    if not found and primary_lang == "java":
        found = _grep_java_mains(base)

    return {"count": len(found), "files": found}


def _generic_preview(path: Path, lines: int = 30) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[:lines])
    except OSError:
        return ""


def _grep_java_mains(base: Path) -> list[dict]:
    results: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fname in filenames:
            if not fname.endswith(".java"):
                continue
            fp = Path(dirpath) / fname
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
                if "public static void main" in text:
                    rel = os.path.relpath(fp, base)
                    results.append({"path": rel, "preview": _java_class_preview(fp)})
                    if len(results) >= 3:
                        return results
            except OSError:
                pass
    return results


# ── Bloque 5: módulos clave ───────────────────────────────────────────────────

_JAVA_KEY_PATTERNS = [
    "**/controller/**/*.java",
    "**/controllers/**/*.java",
    "**/service/**/*.java",
    "**/services/**/*.java",
    "**/repository/**/*.java",
    "**/repositories/**/*.java",
    "**/domain/**/*.java",
    "**/model/**/*.java",
    "**/entity/**/*.java",
    "**/config/**/*.java",
]


def _block_key_modules(base: Path, primary_lang: str) -> dict:
    files: list[dict] = []
    seen: set[str] = set()

    if primary_lang in ("java", "kotlin"):
        ext = ".java" if primary_lang == "java" else ".kt"
        for pattern in _JAVA_KEY_PATTERNS:
            for match in glob.glob(str(base / pattern.replace(".java", ext)), recursive=True):
                rel = os.path.relpath(match, base)
                if rel in seen:
                    continue
                seen.add(rel)
                preview = _java_class_preview(Path(match), lines=30)
                layer = _infer_layer(rel)
                files.append({"path": rel, "layer": layer, "preview": preview})
                if len(files) >= 12:
                    break
            if len(files) >= 12:
                break

    elif primary_lang == "python":
        for pattern in ["**/views.py", "**/models.py", "**/serializers.py",
                        "**/services.py", "**/routes.py", "**/api.py"]:
            for match in glob.glob(str(base / pattern), recursive=True)[:2]:
                rel = os.path.relpath(match, base)
                if rel not in seen:
                    seen.add(rel)
                    files.append({"path": rel, "layer": _infer_layer(rel),
                                  "preview": _generic_preview(Path(match), 25)})

    elif primary_lang in ("javascript", "typescript"):
        for pattern in ["**/routes/**/*.{js,ts}", "**/controllers/**/*.{js,ts}",
                        "**/models/**/*.{js,ts}", "**/services/**/*.{js,ts}"]:
            for match in glob.glob(str(base / pattern), recursive=True)[:2]:
                rel = os.path.relpath(match, base)
                if rel not in seen:
                    seen.add(rel)
                    files.append({"path": rel, "layer": _infer_layer(rel),
                                  "preview": _generic_preview(Path(match), 25)})

    return {"count": len(files), "files": files[:12]}


def _infer_layer(path: str) -> str:
    lower = path.lower()
    for kw, layer in [
        ("controller", "controller"), ("resource", "controller"),
        ("service", "service"), ("usecase", "service"),
        ("repository", "repository"), ("repo", "repository"), ("dao", "repository"),
        ("entity", "domain"), ("domain", "domain"), ("model", "domain"),
        ("config", "config"), ("configuration", "config"),
    ]:
        if kw in lower:
            return layer
    return "other"


# ── Bloque 6: configuración ───────────────────────────────────────────────────

def _block_config(base: Path) -> dict:
    def exists(*parts: str) -> bool:
        return (base / Path(*parts)).exists()

    # CI/CD
    ci_workflows: list[str] = []
    wf_dir = base / ".github" / "workflows"
    if wf_dir.is_dir():
        ci_workflows = sorted(p.name for p in wf_dir.glob("*.yml"))
        ci_workflows += sorted(p.name for p in wf_dir.glob("*.yaml"))

    ci_files: list[str] = []
    for cf in (".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml",
               ".travis.yml", "azure-pipelines.yml", "Makefile"):
        if (base / cf).exists():
            ci_files.append(cf)

    # Docker
    docker_files = [f for f in ("Dockerfile", "docker-compose.yml",
                                 "docker-compose.yaml", "docker-compose.override.yml")
                    if (base / f).exists()]

    # .env files
    dotenv_files = [f.name for f in base.glob(".env*")
                    if f.is_file() and f.name != ".env.example"]

    # Lint / quality
    lint_configs = [f for f in (
        ".eslintrc.json", ".eslintrc.js", ".eslintrc.yml",
        "pylintrc", ".pylintrc", "pyproject.toml",
        ".checkstyle.xml", "checkstyle.xml",
        ".golangci.yml", ".golangci.yaml",
        "sonar-project.properties",
        ".pre-commit-config.yaml",
    ) if (base / f).exists()]

    # OpenAPI / Swagger
    openapi_files = [f for f in (
        "openapi.yaml", "openapi.json", "swagger.yaml",
        "swagger.json", "openapi.yml", "swagger.yml",
    ) if (base / f).exists()]

    return {
        "has_docker":    bool(docker_files),
        "docker_files":  docker_files,
        "has_ci":        bool(ci_workflows or ci_files),
        "ci_workflows":  ci_workflows[:10],
        "ci_files":      ci_files,
        "has_dotenv":    bool(dotenv_files),
        "dotenv_files":  dotenv_files,
        "has_lint":      bool(lint_configs),
        "lint_configs":  lint_configs,
        "has_openapi":   bool(openapi_files),
        "openapi_files": openapi_files,
    }


# ── Bloque 7: estado git ──────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: str) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _block_git(base: Path) -> dict:
    cwd = str(base)

    # current branch
    branch = _run(["git", "branch", "--show-current"], cwd) or None

    # all branches (local + remote, top 20)
    branches_raw = _run(["git", "branch", "-a"], cwd)
    branches = [
        b.strip().lstrip("* ") for b in branches_raw.splitlines()
        if b.strip()
    ][:20]

    # last 10 commits
    log_raw = _run(["git", "log", "--oneline", "-10"], cwd)
    log = [
        {"sha": parts[0], "message": " ".join(parts[1:])}
        for line in log_raw.splitlines()
        if (parts := line.split(None, 1)) and len(parts) == 2
    ]

    # status summary (porcelain v2)
    status_raw = _run(["git", "status", "--porcelain=v2", "--branch"], cwd)
    staged = unstaged = untracked = 0
    for line in status_raw.splitlines():
        if line.startswith("1 ") or line.startswith("2 "):
            xy = line.split(" ", 2)[1]
            if xy[0] != ".":
                staged += 1
            if xy[1] != ".":
                unstaged += 1
        elif line.startswith("? "):
            untracked += 1
    status = {
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "is_clean": staged == 0 and unstaged == 0 and untracked == 0,
    }

    # worktrees
    wt_raw = _run(["git", "worktree", "list", "--porcelain"], cwd)
    worktrees: list[dict] = []
    wt: dict = {}
    for line in wt_raw.splitlines():
        if not line.strip():
            if wt:
                worktrees.append(wt)
                wt = {}
        elif line.startswith("worktree "):
            wt["path"] = line[9:].strip()
        elif line.startswith("branch "):
            wt["branch"] = line[7:].strip().replace("refs/heads/", "")
        elif line.startswith("HEAD "):
            wt["sha"] = line[5:9]
    if wt:
        worktrees.append(wt)

    # submodules
    submod_raw = _run(["git", "submodule", "status"], cwd)
    submodules: list[dict] = []
    for line in submod_raw.splitlines():
        if not line.strip():
            continue
        state_char = line[0]
        parts = line[1:].split()
        if len(parts) >= 2:
            state = {" ": "clean", "+": "modified", "-": "uninitialized", "U": "conflict"}.get(state_char, "unknown")
            submodules.append({"path": parts[1], "sha": parts[0][:8], "state": state})

    return {
        "is_git": bool(branch is not None or branches),
        "branch": branch,
        "branches": branches,
        "recent_commits": log,
        "status": status,
        "worktrees": worktrees,
        "submodules": submodules,
        "submodule_count": len(submodules),
    }


# ── Función principal ─────────────────────────────────────────────────────────

def run(*, path: str = ".", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            base = Path(path).expanduser().resolve()
            if not base.exists():
                return ForgeResult.failure(
                    TOOL, [f"Path not found: {base}"], t.elapsed_ms,
                    suggestion="Provide a valid directory path",
                )

            structure  = _block_structure(base)
            languages  = _block_languages(base)
            build      = _block_build(base)
            primary    = build.get("framework") and languages["primary"] or languages["primary"]
            entry_pts  = _block_entry_points(base, languages["primary"])
            key_mods   = _block_key_modules(base, languages["primary"])
            config     = _block_config(base)
            git        = _block_git(base)

            data = {
                "path": str(base),
                "name": build.get("name") or base.name,
                "version": build.get("version"),
                "description": build.get("description"),
                # 7 blocks
                "structure":    structure,
                "languages":    languages,
                "build":        build,
                "entry_points": entry_pts,
                "key_modules":  key_mods,
                "config":       config,
                "git":          git,
            }
            return ForgeResult.success(TOOL, data, t.elapsed_ms)

        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default=".", help="Path to the project directory (default: .)")


if __name__ == "__main__":
    make_cli(TOOL, "7-block project summary: structure, languages, build, entry-points, key-modules, config, git", run, _add_args)
