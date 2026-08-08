"""Where a repo's agent history lives.

Everything hangs off `git rev-parse --git-common-dir`, which resolves to the *shared*
git directory: the same path from the main worktree and from every linked worktree.
That is what lets Claude in one worktree and Codex in another append to one history.
"""

import subprocess
from pathlib import Path


class NotAGitRepo(Exception):
    """Raised when a path is not inside a git repository."""


def git_common_dir(cwd: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise NotAGitRepo(f"{cwd} is not inside a git repository")
    return Path(result.stdout.strip())


def head_commit(cwd: Path) -> str | None:
    """The commit HEAD points at, or None if the repo has no commits yet."""
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def agentkit_dir(cwd: Path) -> Path:
    return git_common_dir(Path(cwd)) / "agentkit"


def db_path(cwd: Path) -> Path:
    return agentkit_dir(cwd) / "agentkit.db"


def transcripts_dir(cwd: Path, agent: str) -> Path:
    return agentkit_dir(cwd) / "transcripts" / agent
