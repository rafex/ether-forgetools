"""Domain MCP server for git and github workflows."""
from __future__ import annotations

from forgetools.mcp_domain_server import build_domain_server
from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources

server = build_domain_server("forgetools-git", ("git", "gh"))
register_domain_resources(server, "git")
register_domain_prompts(server, "git")


@server.prompt()
def git_stacked_pr_workflow(tasks: str, base: str = "main") -> str:
    """Plan and execute a stacked PR workflow safely."""
    return f"""\
# Stacked PR Workflow

Base branch: `{base}`
Tasks: `{tasks}`

Use this sequence:

1. Run `git_stack_plan(tasks="{tasks}", base="{base}")`.
2. Create each branch in order and keep each PR focused.
3. Run `git_preflight(action="push")` before pushing each branch.
4. Open each PR against the previous branch in the stack.
5. Use `gh_repo_status` to monitor review decisions and checks.
6. Merge from the bottom of the stack only after checks and reviews pass.
"""


@server.prompt()
def git_backport_workflow(commits: str, targets: str) -> str:
    """Plan and execute a safe backport workflow."""
    return f"""\
# Backport Workflow

Commits: `{commits}`
Targets: `{targets}`

Use this sequence:

1. Run `git_backport_plan(commits="{commits}", targets="{targets}")`.
2. Create one backport branch per target release branch.
3. Cherry-pick with `-x` to preserve source commit references.
4. Run release-branch tests.
5. Run `git_preflight(action="push")` before pushing.
6. Open one PR per target branch and monitor with `gh_repo_status`.
"""


@server.prompt()
def git_multi_commit_workflow(scope: str = "current changes") -> str:
    """Split current changes into an explicit multi-commit plan."""
    return f"""\
# Multi-Commit Workflow

Scope: `{scope}`

Use this sequence:

1. Run `git_commit_plan(mode="domain")`.
2. Review the proposed groups and messages.
3. Stage only the files for the first group.
4. Run tests relevant to that group.
5. Commit with the suggested message or a stricter conventional commit.
6. Repeat until no changed files remain.
"""


@server.prompt()
def git_worktree_parallel_merge_workflow(session: str, base_branch: str = "main") -> str:
    """Manage, integrate, and merge multiple worktree tasks safely."""
    return f"""\
# Parallel Worktree Merge Workflow

Session: `{session}`
Base branch: `{base_branch}`

Use this sequence for multiple concurrent changes:

1. Run `git_worktree_workflow(action="status", session="{session}", base_branch="{base_branch}")`.
2. Run `git_worktree_merge_plan(session="{session}", base_branch="{base_branch}")`.
3. For dirty task worktrees, commit or stash changes inside that worktree.
4. For tasks behind integration, run `git_worktree_workflow(action="sync", session="{session}", base_branch="{base_branch}")`.
5. Integrate one ready task at a time with `git_worktree_workflow(action="integrate", task="<task>", session="{session}")`.
6. Run tests from the integration branch after each integration.
7. Finalize with `git_worktree_workflow(action="finalize", session="{session}", target_branch="{base_branch}")`.
8. Use `git_preflight(action="push")` before pushing the final branch.
"""


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
