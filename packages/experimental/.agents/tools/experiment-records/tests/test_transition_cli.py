from __future__ import annotations

import json
from pathlib import Path

from helpers import run_cli, valid_audit, valid_claim, valid_comparison, write_record


def transition(project: Path, experiment_id: str, to_state: str, *extra: str):
    return run_cli(
        "transition",
        str(project),
        experiment_id,
        to_state,
        "--reason",
        f"進入 {to_state}",
        "--occurred-at",
        "2026-01-01T00:00:00Z",
        *extra,
    )


def test_transition_cli_creates_events_without_overwrite(project: Path) -> None:
    first = transition(project, "demo-exp", "draft")
    second = transition(project, "demo-exp", "ready_to_lock")

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert "--reason '進入 draft' --occurred-at 2026-01-01T00:00:00Z" in first.stdout
    assert "Schema：" in first.stdout
    assert "Commit：" in first.stdout
    assert "Evidence：[]" in first.stdout
    lifecycle_dir = project / "records" / "experiments" / "lifecycles"
    assert sorted(path.name for path in lifecycle_dir.glob("*.json")) == [
        "demo-exp-0001.json",
        "demo-exp-0002.json",
    ]
    first_event = json.loads((lifecycle_dir / "demo-exp-0001.json").read_text(encoding="utf-8"))
    assert first_event["to_state"] == "draft"


def test_transition_cli_refuses_existing_output_file(project: Path) -> None:
    lifecycle_dir = project / "records" / "experiments" / "lifecycles"
    lifecycle_dir.mkdir(parents=True)
    reserved = lifecycle_dir / "demo-exp-0001.json"
    reserved.write_text('{"reserved": true}\n', encoding="utf-8")

    result = transition(project, "demo-exp", "draft")

    assert result.returncode == 1
    assert json.loads(reserved.read_text(encoding="utf-8")) == {"reserved": True}


def test_comparison_evidence_must_belong_to_same_experiment(project: Path) -> None:
    comparison = valid_comparison(experiment_id="other-exp")
    write_record(project, "comparisons", "other-comparison", comparison)
    for state in ("draft", "ready_to_lock", "locked", "pilot_running", "promoted", "main_running", "awaiting_comparison"):
        result = transition(project, "demo-exp", state)
        assert result.returncode == 0, result.stdout + result.stderr

    result = transition(
        project,
        "demo-exp",
        "awaiting_claim",
        "--evidence-ref",
        "records/experiments/comparisons/other-comparison.json",
    )

    assert result.returncode == 1
    assert "--evidence-ref records/experiments/comparisons/other-comparison.json" in result.stdout
    assert "設定：reason='進入 awaiting_claim'" in result.stdout
    assert "不屬於 experiment 'demo-exp'" in result.stderr


def test_audit_evidence_follows_claim_to_same_experiment(project: Path) -> None:
    write_record(project, "claims", "other-claim", valid_claim(claim_id="other-claim", experiment_id="other-exp"))
    write_record(project, "audits", "other-audit", valid_audit(claim_id="other-claim"))
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    for state in ("draft", "ready_to_lock", "locked", "pilot_running", "promoted", "main_running", "awaiting_comparison"):
        result = transition(project, "demo-exp", state)
        assert result.returncode == 0, result.stdout + result.stderr
    result = transition(
        project, "demo-exp", "awaiting_claim", "--evidence-ref",
        "records/experiments/comparisons/demo-comparison.json",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    result = transition(
        project,
        "demo-exp",
        "awaiting_review",
        "--evidence-ref",
        "records/experiments/audits/other-audit.json",
    )

    assert result.returncode == 1
    assert "--evidence-ref records/experiments/audits/other-audit.json" in result.stdout
    assert "設定：reason='進入 awaiting_review'" in result.stdout
    assert "不屬於 experiment 'demo-exp'" in result.stderr
