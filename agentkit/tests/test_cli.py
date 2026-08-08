import io
import json
import subprocess
from pathlib import Path

import pytest

from agentkit.cli import main
from agentkit.paths import db_path, transcripts_dir

FIXTURE = Path(__file__).parent / "fixtures" / "claude-session.jsonl"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    (root / "a.txt").write_text("a")
    git("add", "-A", cwd=root)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init", cwd=root)
    monkeypatch.chdir(root)
    return root


def test_init_creates_the_store_and_says_where(repo: Path, capsys):
    assert main(["init"]) == 0

    assert db_path(repo).exists()
    assert str(db_path(repo)) in capsys.readouterr().out


def test_init_is_idempotent_and_keeps_existing_data(repo: Path):
    main(["init"])
    marker = db_path(repo).stat().st_mtime_ns
    (repo / ".git" / "agentkit" / "keep.txt").write_text("survivor")

    assert main(["init"]) == 0

    assert (repo / ".git" / "agentkit" / "keep.txt").read_text() == "survivor"
    assert db_path(repo).stat().st_mtime_ns == marker


def hook_payload(repo: Path) -> str:
    """What Claude Code's SessionEnd hook writes to our stdin."""
    return json.dumps(
        {
            "session_id": "s-001",
            "transcript_path": str(FIXTURE),
            "cwd": str(repo),
            "hook_event_name": "SessionEnd",
        }
    )


def test_a_captured_session_shows_up_in_status(repo: Path, monkeypatch, capsys):
    main(["init"])
    monkeypatch.setattr("sys.stdin", io.StringIO(hook_payload(repo)))

    assert main(["capture", "--stdin"]) == 0
    capsys.readouterr()

    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "s-001" in out
    assert "Add health endpoint" in out
    assert "2 changed" in out

    # The raw transcript is archived alongside the structured record.
    assert (transcripts_dir(repo, "claude") / "s-001.jsonl").exists()


def test_capturing_the_same_session_twice_does_not_duplicate_it(repo: Path, monkeypatch, capsys):
    main(["init"])
    for _ in range(2):
        monkeypatch.setattr("sys.stdin", io.StringIO(hook_payload(repo)))
        assert main(["capture", "--stdin"]) == 0
    capsys.readouterr()

    main(["status"])
    assert capsys.readouterr().out.count("s-001") == 1


def register_hook(repo: Path) -> None:
    settings = repo / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionEnd": [
                        {"hooks": [{"type": "command", "command": "agentkit capture --stdin"}]}
                    ]
                }
            }
        )
    )


def test_capturing_the_archive_itself_is_not_an_error(repo: Path, monkeypatch, capsys):
    main(["init"])
    monkeypatch.setattr("sys.stdin", io.StringIO(hook_payload(repo)))
    main(["capture", "--stdin"])
    archive = transcripts_dir(repo, "claude") / "s-001.jsonl"
    capsys.readouterr()

    # Re-ingesting from the archive is how you rebuild a store; it must not crash.
    payload = json.dumps({"session_id": "s-001", "transcript_path": str(archive), "cwd": str(repo)})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    assert main(["capture", "--stdin"]) == 0
    assert archive.exists()


def test_search_finds_conversation_text_by_substring(repo: Path, monkeypatch, capsys):
    main(["init"])
    monkeypatch.setattr("sys.stdin", io.StringIO(hook_payload(repo)))
    main(["capture", "--stdin"])
    capsys.readouterr()

    assert main(["search", "health"]) == 0
    out = capsys.readouterr().out
    assert "add a health endpoint" in out
    assert "s-001" in out


def test_search_matches_short_queries_including_cjk(repo: Path, monkeypatch, capsys):
    main(["init"])
    monkeypatch.setattr("sys.stdin", io.StringIO(hook_payload(repo)))
    main(["capture", "--stdin"])
    capsys.readouterr()

    # Two-character queries are the common case in Chinese; a tokeniser-based
    # index would silently miss them, so search must be substring-based.
    assert main(["search", "router"]) == 0
    assert "Reading the router first." in capsys.readouterr().out


def test_search_says_so_when_nothing_matches(repo: Path, monkeypatch, capsys):
    main(["init"])
    monkeypatch.setattr("sys.stdin", io.StringIO(hook_payload(repo)))
    main(["capture", "--stdin"])
    capsys.readouterr()

    assert main(["search", "zzzznotpresent"]) == 0
    assert "沒有" in capsys.readouterr().out


def test_doctor_reports_what_is_missing_until_everything_is_wired(repo: Path, capsys):
    assert main(["doctor"]) != 0
    assert "init" in capsys.readouterr().out

    main(["init"])
    capsys.readouterr()
    # Initialised but no hook: nothing would ever be captured, so this is still a failure.
    assert main(["doctor"]) != 0
    assert "SessionEnd" in capsys.readouterr().out

    register_hook(repo)
    assert main(["doctor"]) == 0


def test_doctor_says_nothing_about_any_semantic_index(repo: Path, capsys):
    main(["init"])
    capsys.readouterr()
    main(["doctor"])

    # agentkit owns structured history only. The semantic layer is swappable and
    # must not appear anywhere in this tool.
    out = capsys.readouterr().out.lower()
    for word in ("memsearch", "milvus", "embedding", "semantic", "lancedb"):
        assert word not in out


def test_outside_a_repo_it_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert main(["init"]) != 0
    assert "git" in capsys.readouterr().err.lower()
