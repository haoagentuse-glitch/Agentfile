import io
import json
import subprocess
from pathlib import Path

import pytest

from agentkit.cli import main
from agentkit.paths import export_dir

FIXTURE = Path(__file__).parent / "fixtures" / "claude-session.jsonl"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def captured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    (root / "a.txt").write_text("a")
    git("add", "-A", cwd=root)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init", cwd=root)
    monkeypatch.chdir(root)

    main(["init"])
    payload = json.dumps({"session_id": "s-001", "transcript_path": str(FIXTURE), "cwd": str(root)})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    main(["capture", "--stdin"])
    return root


def test_export_writes_one_markdown_file_per_session(captured: Path, capsys):
    assert main(["export", "--markdown"]) == 0

    out = export_dir(captured) / "s-001.md"
    assert out.exists()
    text = out.read_text()
    assert "add a health endpoint" in text
    assert "Reading the router first." in text
    assert "claude-opus-5" in text
    assert str(out) in capsys.readouterr().out


def test_export_lands_outside_the_working_tree(captured: Path):
    main(["export", "--markdown"])

    # It is a derived cache, not project content: never in the repo, never in docs/.
    assert export_dir(captured).is_relative_to(captured / ".git")
    assert not (captured / "docs").exists()
    assert (
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=captured, capture_output=True, text=True
        ).stdout.strip()
        == ""
    )


def test_export_is_a_projection_and_reflects_the_current_store(captured: Path, tmp_path: Path):
    target = tmp_path / "elsewhere"
    main(["export", "--markdown", str(target)])
    first = (target / "s-001.md").read_text()

    (target / "s-001.md").write_text("手動改動")
    main(["export", "--markdown", str(target)])

    # Rebuildable: the projection is overwritten from SQLite, never merged.
    assert (target / "s-001.md").read_text() == first


def test_export_mentions_no_semantic_backend(captured: Path, capsys):
    main(["export", "--markdown"])

    out = capsys.readouterr().out.lower()
    for word in ("memsearch", "milvus", "embedding", "lancedb"):
        assert word not in out
