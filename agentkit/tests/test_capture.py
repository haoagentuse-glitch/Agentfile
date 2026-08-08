from pathlib import Path

from agentkit.capture import parse_transcript

FIXTURE = Path(__file__).parent / "fixtures" / "claude-session.jsonl"


def test_session_metadata_is_read_from_the_transcript():
    parsed = parse_transcript(FIXTURE)

    assert parsed.session.session_id == "s-001"
    assert parsed.session.agent == "claude"
    assert parsed.session.model == "claude-opus-5"
    assert parsed.session.branch == "main"
    assert parsed.session.cwd == "/repo"
    assert parsed.session.title == "Add health endpoint"
    assert parsed.session.started_at == "2026-08-06T16:30:55.819Z"
    assert parsed.session.ended_at == "2026-08-06T16:32:10.000Z"


def test_tool_calls_are_listed_in_order_and_only_writes_count_as_changes():
    parsed = parse_transcript(FIXTURE)

    assert [call.tool for call in parsed.tool_calls] == ["Read", "Write", "Bash", "Edit"]
    assert parsed.tool_calls[0].timestamp == "2026-08-06T16:31:02.100Z"

    # Reading a file is not a change to it; writing and editing are.
    assert parsed.changed_files == ["/repo/src/health.py", "/repo/src/router.py"]
