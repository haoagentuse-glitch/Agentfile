"""agentfile build 的公開發行契約。"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_build(output: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "agentfile",
            "build",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def built(tmp_path: Path) -> Path:
    output = tmp_path / "dist"
    result = run_build(output)
    assert result.returncode == 0, result.stdout + result.stderr
    return output


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_build_produces_two_complete_copyable_profiles(built: Path) -> None:
    core = built / "core-superpowers"
    experimental = built / "experimental"

    for profile in (core, experimental):
        assert (profile / "AGENTS.md").is_file()
        assert (profile / "CLAUDE.md").is_file()
        assert (profile / ".agents/skills/using-superpowers/SKILL.md").is_file()
        assert (profile / ".claude/skills/using-superpowers/SKILL.md").is_file()
        assert not (profile / ".claude/skills").is_symlink()

    assert not (core / ".agents/skills/experiment-design").exists()
    assert (experimental / ".agents/skills/experiment-design/SKILL.md").is_file()
    assert (experimental / ".agents/tools/experiment-records/pyproject.toml").is_file()
    assert (
        experimental / "records/experiments/schemas/experiment-contract.schema.json"
    ).is_file()


def test_claude_and_codex_receive_identical_physical_skill_trees(built: Path) -> None:
    for profile_name in ("core-superpowers", "experimental"):
        profile = built / profile_name
        assert tree_hashes(profile / ".agents/skills") == tree_hashes(
            profile / ".claude/skills"
        )


def test_removed_projection_and_grill_mechanisms_are_not_distributed(
    built: Path,
) -> None:
    for profile_name in ("core-superpowers", "experimental"):
        profile = built / profile_name
        assert not (profile / ".agentfile").exists()
        assert not (profile / "apply.sh").exists()
        for removed in ("grill-me", "grilling", "grill-with-docs", "upstream-feedback"):
            assert not (profile / ".agents/skills" / removed).exists()


def test_rebuild_replaces_only_the_configured_output(built: Path) -> None:
    junk = built / "core-superpowers/junk.txt"
    junk.write_text("stale", encoding="utf-8")
    sibling = built.parent / "keep.txt"
    sibling.write_text("keep", encoding="utf-8")

    result = run_build(built)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not junk.exists()
    assert sibling.read_text(encoding="utf-8") == "keep"


def test_build_is_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert run_build(first).returncode == 0
    assert run_build(second).returncode == 0
    assert tree_hashes(first) == tree_hashes(second)
