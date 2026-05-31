"""forgetools.release.precheck - Run basic pre-release checks."""
from __future__ import annotations

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer
from forgetools._runner import run_command


def run(*, cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        checks = []
        for name, cmd in {
            "git_status": ["git", "status", "--porcelain"],
            "git_branch": ["git", "branch", "--show-current"],
            "latest_tag": ["git", "describe", "--tags", "--abbrev=0"],
        }.items():
            rc, stdout, stderr = run_command(cmd, cwd=cwd, timeout=20)
            checks.append({"name": name, "ok": rc == 0, "stdout": stdout.strip(), "stderr": stderr.strip()})
        dirty = next((c["stdout"] for c in checks if c["name"] == "git_status"), "")
        return ForgeResult.success("release.precheck", {"checks": checks, "is_clean": dirty == ""}, t.elapsed_ms)


if __name__ == "__main__":
    make_cli("release.precheck", "Run basic pre-release checks", run)
