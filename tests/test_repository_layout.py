"""Agentfile 本體與可發行來源必須分離。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_repository_has_no_legacy_projection_source_tree() -> None:
    assert not (ROOT / "apply.sh").exists()
    assert not (ROOT / "core").exists()
    assert not (ROOT / "profiles").exists()
    assert not list(ROOT.glob("**/upstream-feedback/SKILL.md"))
    assert (ROOT / "packages/core-superpowers").is_dir()
    assert (ROOT / "packages/experimental").is_dir()
    assert (ROOT / "examples/experimental/rag-walkthrough/README.md").is_file()
