from __future__ import annotations

import subprocess
from pathlib import Path

from forgetools.git.operations import run


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "forgetools tests")
    _git(repo, "config", "user.email", "tests@example.invalid")
    (repo / "README.md").write_text("initial\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "chore: initial")
    return repo


def test_read_only_git_operations_return_structured_data(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    remote = run(action="remote", cwd=str(repo))
    show = run(action="show", cwd=str(repo), max_lines=20)
    reflog = run(action="reflog", cwd=str(repo), count=2)

    assert remote.ok
    assert remote.data["remotes"] == []
    assert show.ok and "chore: initial" in show.data["output"]
    assert reflog.ok and reflog.data["output"]


def test_mutating_git_operations_preview_by_default(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    result = run(action="switch", cwd=str(repo), branch="feature/test", create=True)

    assert result.ok
    assert result.data["preview"] is True
    assert result.data["executed"] is False
    assert "git switch --create feature/test" in result.data["command"]


def test_mutating_git_operations_require_confirmation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    result = run(action="reset", cwd=str(repo), ref="HEAD", execute=True)

    assert not result.ok
    assert "confirmation" in result.errors[0].lower()


def test_confirmed_switch_executes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    result = run(
        action="switch",
        cwd=str(repo),
        branch="feature/test",
        create=True,
        execute=True,
        confirm=True,
    )

    assert result.ok
    assert result.data["executed"] is True
    current = subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
    assert current == "feature/test"


def test_branch_remote_and_maintenance_operations_preview(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    branch = run(action="branch-create", cwd=str(repo), branch="feature/new")
    remote = run(
        action="remote-add",
        cwd=str(repo),
        remote="upstream",
        remote_url="https://example.invalid/upstream.git",
    )
    maintenance = run(action="maintenance", cwd=str(repo), maintenance_action="gc")

    assert branch.ok and "git branch feature/new HEAD" in branch.data["command"]
    assert remote.ok and remote.data["requires_confirmation"] is True
    assert maintenance.ok and maintenance.data["command"] == "git gc"


def test_revert_and_bisect_require_explicit_parameters(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    revert = run(action="revert", cwd=str(repo), ref="HEAD")
    bisect = run(action="bisect", cwd=str(repo), bisect_action="good", ref="HEAD")

    assert revert.ok and "git revert --no-edit HEAD" in revert.data["command"]
    assert bisect.ok and "git bisect good HEAD" in bisect.data["command"]
