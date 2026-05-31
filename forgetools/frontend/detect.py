"""forgetools.frontend.detect - Detect common frontend stacks."""
from __future__ import annotations

import json
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer


def run(*, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        root = Path(cwd or ".").resolve()
        pkg_path = root / "package.json"
        data: dict = {"root": str(root), "has_package_json": pkg_path.exists(), "frameworks": [], "package_manager": None}
        if (root / "pnpm-lock.yaml").exists():
            data["package_manager"] = "pnpm"
        elif (root / "yarn.lock").exists():
            data["package_manager"] = "yarn"
        elif (root / "bun.lockb").exists():
            data["package_manager"] = "bun"
        elif (root / "package-lock.json").exists():
            data["package_manager"] = "npm"

        if pkg_path.exists():
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            checks = {
                "next": "Next.js",
                "vite": "Vite",
                "astro": "Astro",
                "svelte": "Svelte/SvelteKit",
                "react": "React",
                "vue": "Vue",
                "@angular/core": "Angular",
            }
            data["frameworks"] = [label for dep, label in checks.items() if dep in deps]
            data["scripts"] = pkg.get("scripts", {})
        return ForgeResult.success("frontend.detect", data, t.elapsed_ms)


if __name__ == "__main__":
    make_cli("frontend.detect", "Detect common frontend stacks", run)
