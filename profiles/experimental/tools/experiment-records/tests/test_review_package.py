"""獨立審核包：審核者只收到凍結的事實與證據摘錄，看不到誰寫的。

包裡有 producer，獨立性就守不住——知道是哪個 agent 用哪版 prompt 寫的，就會被它帶著走。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from helpers import (
    run_cli,
    valid_audit,
    valid_claim,
    valid_comparison,
    valid_definition,
    valid_run,
    write_config,
    write_record,
)

AGENT = {
    "kind": "software_agent",
    "name": "claim-writer",
    "model": "anthropic/claude-opus-5",
    "prompt_id": "house-writer@1",
    "created_at": "2026-01-01T00:00:00Z",
}


def _metric(**overrides: object) -> dict:
    entry = {
        "definition_consistent": True, "computed": True,
        "baseline": 0.62, "treatment": 0.71,
        "absolute_diff": 0.09, "relative_diff": 0.145,
    }
    entry.update(overrides)
    return entry


@pytest.fixture
def scenario(project: Path):
    def build(*, definition_overrides: dict | None = None, claim_overrides: dict | None = None,
              audit_overrides: dict | None = None) -> Path:
        write_config(project, "records/experiments/configs/baseline.yaml")
        write_config(project, "records/experiments/configs/treatment.yaml")
        write_record(project, "definitions", "demo-exp", valid_definition(**(definition_overrides or {})))
        write_record(project, "comparisons", "demo-comparison",
                     valid_comparison(metrics={"recall_at_10": _metric()}))
        write_record(project, "runs", "demo-run-1", valid_run(seed=42))
        write_record(project, "runs", "demo-run-2", valid_run(
            run_id="demo-run-2", status="invalid", invalid_reason="第 40 筆查詢逾時",
            failure={"class": "execution", "phase": "execution"},
        ))
        claim = {
            "producer": dict(AGENT),
            "evidence_refs": [{
                "kind": "comparison",
                "ref": "records/experiments/comparisons/demo-comparison.json",
                "locator": "metrics.recall_at_10.absolute_diff",
            }],
        }
        claim.update(claim_overrides or {})
        write_record(project, "claims", "demo-claim", valid_claim(**claim))
        if audit_overrides is not None:
            write_record(project, "audits", "demo-claim", valid_audit(**audit_overrides))
        return project

    return build


def _package(project: Path, claim_id: str = "demo-claim") -> dict:
    output = project / "review-package.json"
    result = run_cli("review-package", str(project), claim_id, "--output", str(output))
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(output.read_text(encoding="utf-8"))


def test_package_carries_the_frozen_question_and_the_claim(scenario) -> None:
    package = _package(scenario())

    assert package["claim_id"] == "demo-claim"
    assert package["question"]["question"]
    assert package["question"]["primary_metric"] == "recall_at_10"
    assert package["claim"]["statement"]
    assert package["claim"]["scope"]


def _keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {key for value in node.values() for key in _keys(value)}
    if isinstance(node, list):
        return {key for item in node for key in _keys(item)}
    return set()


def test_package_never_carries_a_producer(scenario) -> None:
    """審核者不該知道這個主張是誰寫的。"""
    package = _package(scenario())

    # omitted 是給人讀的說明文字，會提到 producer 這個字；這裡檢查的是結構裡沒有這個欄位。
    assert "producer" not in _keys(package)
    assert any("producer" in line for line in package["omitted"])


def test_evidence_excerpt_resolves_the_actual_value(scenario) -> None:
    """審核者不必相信主張對數字的轉述——包裡直接放取出來的值。"""
    package = _package(scenario())

    [excerpt] = package["evidence_excerpts"]
    assert excerpt["resolved"] is True
    assert excerpt["value"] == 0.09


def test_unresolvable_locator_is_marked_not_silently_filled(scenario) -> None:
    package = _package(scenario(claim_overrides={
        "evidence_refs": [{
            "kind": "comparison",
            "ref": "records/experiments/comparisons/demo-comparison.json",
            "locator": "metrics.no_such_metric.absolute_diff",
        }],
    }))

    [excerpt] = package["evidence_excerpts"]
    assert excerpt["resolved"] is False
    assert "value" not in excerpt
    assert "取不到值" in excerpt["problem"]


def test_failed_runs_are_included_in_the_package(scenario) -> None:
    """只放成功的 run 會讓審核者看到一個比實際乾淨的世界。"""
    package = _package(scenario())

    by_id = {run["run_id"]: run for run in package["runs"]}
    assert by_id["demo-run-2"]["status"] == "invalid"
    assert by_id["demo-run-2"]["failure_class"] == "execution"
    assert by_id["demo-run-2"]["invalid_reason"]


def test_all_three_comparability_judgements_are_visible(scenario) -> None:
    package = _package(scenario())

    for field in ("comparison_valid", "confounded", "structurally_comparable", "controlled_variables_match"):
        assert field in package["comparison"]


def test_mechanical_results_are_attached_when_an_audit_exists(scenario) -> None:
    package = _package(scenario(audit_overrides={}))

    assert package["mechanical"]["mechanical_pass"] is True


def test_policy_defaults_to_any_independent(scenario) -> None:
    package = _package(scenario())

    assert package["policy"]["required_reviewer_kind"] == "any_independent"


def test_policy_comes_from_the_frozen_contract(scenario) -> None:
    package = _package(scenario(definition_overrides={
        "review_policy": {"required_reviewer_kind": "human", "min_reviewers": 2}
    }))

    assert package["policy"] == {"required_reviewer_kind": "human", "min_reviewers": 2}


def test_missing_claim_is_an_error_not_an_empty_package(project: Path) -> None:
    result = run_cli("review-package", str(project), "no-such-claim")

    assert result.returncode == 1
    assert "找不到 claim_id" in result.stderr


def test_audit_must_satisfy_the_frozen_review_policy(scenario) -> None:
    """看到結果之後才放寬審核標準，等於沒有審核。"""
    project = scenario(
        definition_overrides={"review_policy": {"required_reviewer_kind": "human"}},
        audit_overrides={"review_independence": {"independent": True, "reviewer_kind": "second_model"}},
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "不滿足 Contract 凍結的 required_reviewer_kind='human'" in result.stdout


def test_audit_satisfying_the_policy_passes(scenario) -> None:
    project = scenario(
        definition_overrides={"review_policy": {"required_reviewer_kind": "second_model"}},
        audit_overrides={"review_independence": {"independent": True, "reviewer_kind": "human"}},
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_policy_requires_the_audit_to_state_a_reviewer_kind(scenario) -> None:
    project = scenario(
        definition_overrides={"review_policy": {"required_reviewer_kind": "second_model"}},
        audit_overrides={"review_independence": {"independent": True}},
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "沒有記錄 reviewer_kind" in result.stdout


def test_no_policy_means_no_reviewer_kind_requirement(scenario) -> None:
    project = scenario(audit_overrides={"review_independence": {"independent": True}})

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
