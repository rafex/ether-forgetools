"""forgetools.git.backport_plan - Plan safe cherry-pick backports to release branches."""
from __future__ import annotations

import argparse

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer


def run(*, commits: str, targets: str, branch_prefix: str = "backport", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        commit_list = [item.strip() for item in commits.split(",") if item.strip()]
        target_list = [item.strip() for item in targets.split(",") if item.strip()]
        if not commit_list:
            return ForgeResult.failure("git.backport-plan", ["No commits provided"], t.elapsed_ms, "Pass --commits sha1,sha2")
        if not target_list:
            return ForgeResult.failure("git.backport-plan", ["No target branches provided"], t.elapsed_ms, "Pass --targets release/1.2,release/1.3")

        plans = []
        for target in target_list:
            safe_target = target.replace("/", "-")
            branch = f"{branch_prefix}/{safe_target}"
            commands = [
                f"git fetch origin {target}",
                f"git switch -c {branch} origin/{target}",
                *[f"git cherry-pick -x {sha}" for sha in commit_list],
                "# run target branch tests",
                f"git push -u origin {branch}",
                f"gh pr create --base {target} --head {branch} --title 'backport: {', '.join(commit_list)} to {target}'",
            ]
            plans.append({"target": target, "branch": branch, "commits": commit_list, "commands": commands})
        return ForgeResult.success("git.backport-plan", {"plans": plans, "note": "Plan only; no git commands were executed."}, t.elapsed_ms)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--commits", required=True, help="Comma-separated commit SHAs to cherry-pick")
    p.add_argument("--targets", required=True, help="Comma-separated release branches")
    p.add_argument("--branch-prefix", default="backport", help="Backport branch prefix")


if __name__ == "__main__":
    make_cli("git.backport-plan", "Plan safe cherry-pick backports to release branches", run, _args)
