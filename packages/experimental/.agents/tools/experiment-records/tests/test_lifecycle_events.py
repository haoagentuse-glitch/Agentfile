from __future__ import annotations

import json
from pathlib import Path

from helpers import run_cli, valid_lifecycle, write_record


def test_lifecycle_is_stored_as_immutable_transition_events(project: Path) -> None:
    write_record(project, "lifecycles", "demo-exp", valid_lifecycle("draft", "ready_to_lock"))

    event_paths = sorted((project / "records" / "experiments" / "lifecycles").glob("*.json"))
    assert [path.name for path in event_paths] == ["demo-exp-0001.json", "demo-exp-0002.json"]
    for path in event_paths:
        event = json.loads(path.read_text(encoding="utf-8"))
        assert "current_state" not in event
        assert "history" not in event


def test_awaiting_review_requires_audit_record_evidence(project: Path) -> None:
    lifecycle = valid_lifecycle(
        "draft", "ready_to_lock", "locked", "pilot_running", "promoted",
        "main_running", "awaiting_comparison", "awaiting_claim", "awaiting_review",
    )
    lifecycle["history"][-1]["evidence_refs"] = [
        "records/experiments/comparisons/demo-comparison.json"
    ]
    write_record(project, "lifecycles", "demo-exp", lifecycle)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "進入 awaiting_review 必須引用 audits/ record" in result.stdout


def test_revise_requires_evidence_not_used_by_earlier_event(project: Path) -> None:
    lifecycle = valid_lifecycle(
        "draft", "ready_to_lock", "locked", "pilot_running", "promoted", "main_running",
        "awaiting_comparison", "awaiting_claim", "awaiting_review", "revise",
    )
    lifecycle["history"][-1]["updated_definition_fields"] = ["/hypothesis"]
    lifecycle["history"][-1]["evidence_refs"] = [
        "records/experiments/audits/demo-audit.json"
    ]
    write_record(project, "lifecycles", "demo-exp", lifecycle)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "先前未使用的新證據" in result.stdout


def test_lifecycle_transition_table_values_must_be_string_arrays(project: Path) -> None:
    schema_path = project / "records" / "experiments" / "schemas" / "lifecycle-state.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["x-allowed-transitions"]["draft"] = "ready_to_lock"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "每個轉移出口必須是 state 字串陣列" in result.stdout
