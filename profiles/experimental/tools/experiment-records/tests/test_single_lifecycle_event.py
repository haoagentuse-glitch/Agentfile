from pathlib import Path

from helpers import run_cli, valid_lifecycle, write_record


def test_single_lifecycle_event_does_not_require_sibling_history(project: Path) -> None:
    last_event = write_record(
        project,
        "lifecycles",
        "demo-exp",
        valid_lifecycle("draft", "ready_to_lock", "locked"),
    )

    result = run_cli("validate", str(last_event))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "事件不連續" not in result.stdout
