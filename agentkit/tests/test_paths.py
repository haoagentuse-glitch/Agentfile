import subprocess
from pathlib import Path

import pytest

from agentkit.paths import NotAGitRepo, agentkit_dir


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    (root / "a.txt").write_text("a")
    git("add", "-A", cwd=root)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init", cwd=root)
    return root


def test_linked_worktrees_share_one_agentkit_dir(repo: Path, tmp_path: Path):
    linked = tmp_path / "wt"
    git("worktree", "add", "-q", str(linked), "-b", "side", cwd=repo)

    # The whole point: Claude in one worktree and Codex in another write the same history.
    assert agentkit_dir(linked) == agentkit_dir(repo)


def test_the_dir_is_absolute_and_lives_under_the_shared_git_dir(repo: Path):
    resolved = agentkit_dir(repo)

    assert resolved.is_absolute()
    assert resolved == repo / ".git" / "agentkit"


def test_outside_a_repo_it_refuses_rather_than_guessing(tmp_path: Path):
    with pytest.raises(NotAGitRepo):
        agentkit_dir(tmp_path)
