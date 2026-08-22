"""claim 與 audit 的稽核軸線，以及兩者之間的關係。

稽核刻意分成互不取代的幾個軸。技術上正確但答非所問、推論成立卻超出證據範圍、
自寫自審後自動接受——這幾種失效模式在單一布林值下全都看不出來。
"""

from __future__ import annotations

from pathlib import Path

from helpers import run_cli, valid_audit, valid_claim, valid_comparison, write_record


def _agent(name: str, prompt_id: str) -> dict:
    return {
        "kind": "software_agent",
        "name": name,
        "model": "anthropic/claude-opus-5",
        "prompt_id": prompt_id,
        "created_at": "2026-01-01T00:00:00Z",
    }


def _chain(project: Path, claim_overrides: dict, audit_overrides: dict) -> None:
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(project, "claims", "demo-claim", valid_claim(**claim_overrides))
    write_record(project, "audits", "demo-audit", valid_audit(**audit_overrides))


def test_full_audit_axes_are_expressible(project: Path) -> None:
    _chain(
        project,
        {
            "claim_type": "comparative",
            "status": "supported",
            "evidence_refs": [{
                "kind": "comparison",
                "ref": "records/experiments/comparisons/demo-comparison.json",
                "locator": "metrics.recall_at_10.absolute_diff",
                "hash": "sha256:abc",
            }],
            "producer": _agent("claim-writer", "claim-writer@1"),
        },
        {
            "entailment": {"verdict": "entailed", "reasoning": "差異方向與幅度都由比較結果直接得出"},
            "intended_question_fit": {"verdict": "answers", "reasoning": "正面回答 definition.question"},
            "novelty": {"status": "not_applicable"},
            "review_independence": {"independent": True, "reviewer_kind": "second_model"},
            "producer": _agent("evidence-reviewer", "evidence-reviewer@1"),
        },
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_self_review_must_declare_itself_not_independent(project: Path) -> None:
    """同一個 agent 用同一版 prompt 自寫自審，就不是獨立審核。"""
    writer = _agent("claim-writer", "claim-writer@1")
    _chain(
        project,
        {"producer": writer},
        {"producer": dict(writer), "review_independence": {"independent": True}},
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "review_independence.independent 必須是 false" in result.stdout


def test_self_review_declared_honestly_passes(project: Path) -> None:
    writer = _agent("claim-writer", "claim-writer@1")
    _chain(
        project,
        {"producer": writer},
        {
            "producer": dict(writer),
            "review_independence": {"independent": False, "reviewer_kind": "same_context"},
            "final_verdict": "partially_supported",
            "scope_verdict": "partially_supported",
        },
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_non_independent_review_cannot_fully_support(project: Path) -> None:
    _chain(
        project,
        {},
        {"review_independence": {"independent": False}, "final_verdict": "fully_supported"},
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "不得是 fully_supported" in result.stdout


def test_same_context_reviewer_cannot_claim_independence(project: Path) -> None:
    _chain(
        project,
        {},
        {"review_independence": {"independent": True, "reviewer_kind": "same_context"}},
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "same_context 不可能是獨立審核" in result.stdout


def test_failed_mechanical_check_cannot_end_supported(project: Path) -> None:
    _chain(
        project,
        {},
        {
            "mechanical": {
                "reference_exists": False, "comparison_valid": None, "estimand_exists": None,
                "direction_matches": None, "conclusion_matches": True, "magnitude_matches": None, "mechanical_pass": False,
            },
            "scope_verdict": "unauditable",
            "final_verdict": "fully_supported",
        },
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "mechanical_pass 為 false" in result.stdout


def test_claim_cannot_be_supported_without_an_audit(project: Path) -> None:
    """無稽核撐著的結論不得進 supported。"""
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(project, "claims", "demo-claim", valid_claim(status="supported"))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "沒有對應的 claim-audit-result" in result.stdout


def test_claim_cannot_be_supported_when_audit_disagrees(project: Path) -> None:
    _chain(
        project,
        {"status": "supported"},
        {"scope_verdict": "overreaching", "final_verdict": "overreaching"},
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "稽核結論是 'overreaching'" in result.stdout


def test_inconclusive_is_a_legal_final_state(project: Path) -> None:
    """證據不足是正式結果，不是待辦。"""
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(project, "claims", "demo-claim", valid_claim(status="inconclusive"))

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_negative_result_claim_type_is_legal(project: Path) -> None:
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(
        project, "claims", "demo-claim",
        valid_claim(claim_type="negative_result", status="refuted"),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_superseded_claim_must_name_its_replacement(project: Path) -> None:
    """舊結論保留、不刪除；但要說得出被誰取代。"""
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(project, "claims", "demo-claim", valid_claim(status="superseded"))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "superseded_by" in result.stdout


def test_audit_for_a_missing_claim_is_rejected(project: Path) -> None:
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(project, "audits", "demo-audit", valid_audit())

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "不存在" in result.stdout


def test_novelty_confirmed_without_sources_is_rejected(project: Path) -> None:
    _chain(project, {}, {"novelty": {"status": "novel_confirmed", "source_refs": []}})

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "未查證只能標 unverified" in result.stdout


def test_evidence_ref_must_resolve(project: Path) -> None:
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(
        project, "claims", "demo-claim",
        valid_claim(evidence_refs=[{"kind": "run", "ref": "records/experiments/runs/missing.json"}]),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "evidence_refs.0.ref" in result.stdout


def test_vacuous_answer_is_expressible_alongside_a_passing_mechanical_check(project: Path) -> None:
    """數字全對、卻沒有回答原本的問題——這正是要分軸才看得出來的情況。"""
    _chain(
        project,
        {},
        {
            "entailment": {"verdict": "entailed"},
            "intended_question_fit": {
                "verdict": "vacuous",
                "reasoning": "只重述了比較結果，沒有回答機制問題",
            },
            "scope_verdict": "partially_supported",
            "final_verdict": "partially_supported",
        },
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
