"""forgetools.diag.health — Check availability of required tools."""
from __future__ import annotations

import shutil

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "diag.health"

TOOLS = {
    "git": "Install: https://git-scm.com",
    "gh": "Install: brew install gh",
    "kubectl": "Install: brew install kubectl",
    "mvn": "Install: brew install maven",
    "gradle": "Install: brew install gradle",
    "rg": "Install: brew install ripgrep",
    "python3": "Should be pre-installed",
    "java": "Install: brew install openjdk",
}


def run(*, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        results = {}
        missing = []
        for tool, hint in TOOLS.items():
            path = shutil.which(tool)
            results[tool] = {"available": path is not None, "path": path, "install_hint": hint if not path else None}
            if not path:
                missing.append(tool)

        ok = len(missing) == 0
        return ForgeResult(
            ok=ok,
            tool=TOOL,
            data={"tools": results, "missing": missing, "all_available": ok},
            duration_ms=t.elapsed_ms,
            suggestion=f"Missing tools: {', '.join(missing)}" if missing else None,
        )


if __name__ == "__main__":
    make_cli(TOOL, "Check availability of required tools", run)
