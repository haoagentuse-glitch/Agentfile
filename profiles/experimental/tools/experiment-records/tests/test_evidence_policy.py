from __future__ import annotations

from experiment_records.evidence_policy import evaluate_evidence_policy


def _run(run_id: str, *, stage: str, baseline_run: str | None) -> dict:
    return {
        "run_id": run_id,
        "experiment_id": "demo-exp",
        "stage": stage,
        "baseline_run": baseline_run,
        "status": "completed",
    }


def test_eligible_pair_must_have_allowed_stages_and_unambiguous_roles() -> None:
    contract = {"experiment_id": "demo-exp", "evidence_policy": {"eligible_run_stages": ["main", "replication"]}}
    baseline = _run("baseline", stage="main", baseline_run=None)
    treatment = _run("treatment", stage="replication", baseline_run="baseline")

    assert evaluate_evidence_policy(contract, [treatment, baseline]) == {
        "eligible": True,
        "reasons": [],
        "roles": {"baseline": "baseline", "treatment": "treatment"},
    }


def test_ineligible_stage_reports_each_disallowed_run_without_hard_coding_diagnostic() -> None:
    contract = {"experiment_id": "demo-exp", "evidence_policy": {"eligible_run_stages": ["pilot"]}}
    baseline = _run("baseline", stage="main", baseline_run=None)
    treatment = _run("treatment", stage="diagnostic", baseline_run="baseline")

    result = evaluate_evidence_policy(contract, [baseline, treatment])

    assert result["eligible"] is False
    assert result["reasons"] == [
        "run 'baseline' stage 'main' 不在 evidence_policy.eligible_run_stages ('pilot',)",
        "run 'treatment' stage 'diagnostic' 不在 evidence_policy.eligible_run_stages ('pilot',)",
    ]


def test_role_resolution_fails_closed_when_lineage_is_ambiguous() -> None:
    contract = {"experiment_id": "demo-exp", "evidence_policy": {"eligible_run_stages": ["main"]}}
    first = _run("first", stage="main", baseline_run=None)
    second = _run("second", stage="main", baseline_run=None)

    assert evaluate_evidence_policy(contract, [first, second]) == {
        "eligible": False,
        "reasons": ["無法由 baseline_run lineage 唯一解析 baseline 與 treatment 角色"],
        "roles": None,
    }


def test_single_run_with_explicit_lineage_role_is_eligible() -> None:
    contract = {"experiment_id": "demo-exp", "evidence_policy": {"eligible_run_stages": ["pilot"]}}
    baseline = _run("baseline", stage="pilot", baseline_run=None)

    assert evaluate_evidence_policy(contract, [baseline])["roles"] == {
        "baseline": "baseline"
    }


def test_missing_or_invalid_policy_fails_closed() -> None:
    baseline = _run("baseline", stage="main", baseline_run=None)
    treatment = _run("treatment", stage="main", baseline_run="baseline")

    assert evaluate_evidence_policy({}, [baseline, treatment])["eligible"] is False
    assert evaluate_evidence_policy(
        {"experiment_id": "demo-exp", "evidence_policy": {"eligible_run_stages": []}}, [baseline, treatment]
    )["eligible"] is False


def test_wrong_experiment_and_duplicate_ids_fail_closed() -> None:
    contract = {
        "experiment_id": "demo-exp",
        "evidence_policy": {"eligible_run_stages": ["main"]},
    }
    baseline = _run("same", stage="main", baseline_run=None)
    treatment = _run("same", stage="main", baseline_run="same")
    treatment["experiment_id"] = "other-exp"

    result = evaluate_evidence_policy(contract, [baseline, treatment])

    assert result["eligible"] is False
    assert any("run_id 重複" in reason for reason in result["reasons"])
    assert any("不屬於目標 experiment" in reason for reason in result["reasons"])


def test_invalid_run_id_fails_closed_without_crashing() -> None:
    contract = {
        "experiment_id": "demo-exp",
        "evidence_policy": {"eligible_run_stages": ["main"]},
    }
    run = _run("valid-before-corruption", stage="main", baseline_run=None)
    run["run_id"] = ["not", "hashable"]

    result = evaluate_evidence_policy(contract, [run], required_roles=frozenset())

    assert result["eligible"] is False
    assert "run_id 缺少或不是非空字串" in result["reasons"]
