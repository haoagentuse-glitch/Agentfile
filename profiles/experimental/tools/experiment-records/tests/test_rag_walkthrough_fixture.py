"""RAG 貫穿式骨架 fixture 必須整包通過驗證，而且真的走完整條鏈。

fixture 放在 profiles/experimental/fixtures/rag-walkthrough/，不含 schemas——
schemas 只有 records/experiments/schemas/ 一份，這裡在暫存目錄組起來再驗證。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from helpers import run_cli


def _find(relative: str) -> Path:
    for candidate in Path(__file__).resolve().parents:
        probe = candidate / relative
        if probe.exists():
            return probe
    raise RuntimeError(f"找不到 {relative}")


WALKTHROUGH = _find("fixtures/rag-walkthrough")
SCHEMAS = _find("records/experiments/schemas")
PROMPTS = _find("records/experiments/prompts")


@pytest.fixture(scope="module")
def walkthrough(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("walkthrough") / "project"
    shutil.copytree(WALKTHROUGH, root)
    # schemas 與 prompts 各只有一份，不在 fixture 裡複製一次；組起來才驗證，
    # 這樣 fixture 記的 prompt_hash 就必須跟真的 prompt 檔案對得上。
    shutil.copytree(SCHEMAS, root / "records" / "experiments" / "schemas")
    shutil.copytree(PROMPTS, root / "records" / "experiments" / "prompts")
    return root


def _records(root: Path, subdir: str) -> dict[str, dict]:
    directory = root / "records" / "experiments" / subdir
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    }


def test_whole_walkthrough_validates(walkthrough: Path) -> None:
    result = run_cli("validate", str(walkthrough))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "\n錯誤" not in f"\n{result.stdout}"


def test_every_lifecycle_chain_reaches_a_declared_terminal_state(walkthrough: Path) -> None:
    result = run_cli("validate", str(walkthrough))

    for experiment_id, terminal in {
        "rag-topk-recall": "accepted",
        "rag-chunk-overlap": "confounded",
        "rag-rerank-depth": "execution_failed",
        "rag-query-rewrite": "inconclusive",
    }.items():
        assert f"lifecycles/{experiment_id}: 生命週期轉移合法；事件序列完整；目前狀態={terminal}" in result.stdout


def test_locked_definition_carries_a_full_certificate(walkthrough: Path) -> None:
    definition = _records(walkthrough, "definitions")["rag-topk-recall"]

    assert definition["status"] == "locked"
    derivation = definition["derivation"]
    assert {p["id"] for p in derivation["primitives"]} == {"retrieval_coverage", "context_noise"}
    assert {a["id"] for a in derivation["assumptions"]} == {"a1", "a2", "a3"}
    # 每一條 failure_update 都指回真的存在的 assumption。
    assert {r["update_assumption_id"] for r in derivation["failure_update"]} <= {a["id"] for a in derivation["assumptions"]}
    assert derivation["novelty_status"] == "novel_claimed"
    assert derivation["source_refs"]


def test_pilot_gate_and_three_replications_are_present(walkthrough: Path) -> None:
    runs = _records(walkthrough, "runs")
    stages: dict[str, list[str]] = {}
    for run in runs.values():
        if run["experiment_id"] == "rag-topk-recall":
            stages.setdefault(run["stage"], []).append(run["run_id"])

    assert sorted(stages["pilot"]) == ["topk-pilot-baseline", "topk-pilot-treatment"]
    assert sorted(stages["main"]) == ["topk-main-baseline", "topk-main-treatment"]
    assert len([r for r in stages["replication"] if runs[r]["status"] == "completed"]) == 3

    gate = _records(walkthrough, "gates")["rag-topk-recall"]
    assert [entry["level"] for entry in gate["history"]] == ["L0", "L3", "L4"]
    assert gate["current_level"] == "L4"


def test_the_failed_replication_is_kept_not_dropped(walkthrough: Path) -> None:
    """刪掉失敗的複現會讓紀錄看起來剛好是三次成功，那是選擇性報告。"""
    failed = _records(walkthrough, "runs")["topk-replication-4-oom"]

    assert failed["status"] == "invalid"
    assert failed["failure"]["class"] == "execution"
    assert failed["failure"]["exit_code"] == 137
    assert failed["failure"]["retriable"] is True


def test_accepted_claim_is_backed_by_an_independent_audit(walkthrough: Path) -> None:
    claim = _records(walkthrough, "claims")["topk-recall-claim"]
    audit = _records(walkthrough, "audits")["topk-recall-claim"]

    assert claim["status"] == "supported"
    assert audit["final_verdict"] == "fully_supported"
    assert audit["review_independence"]["independent"] is True
    assert audit["producer"]["name"] != claim["producer"]["name"]


def test_audit_records_a_gap_the_mechanical_pass_cannot_see(walkthrough: Path) -> None:
    """數字全對、卻沒有完整回答原本的問題——這正是分軸的用處。"""
    audit = _records(walkthrough, "audits")["topk-recall-claim"]

    assert audit["mechanical"]["mechanical_pass"] is True
    assert audit["scope_verdict"] == "fully_supported"
    assert audit["intended_question_fit"]["verdict"] == "partially_answers"
    assert audit["novelty"]["status"] == "prior_art_found"


def test_confounded_counterexample_is_present(walkthrough: Path) -> None:
    comparison = _records(walkthrough, "comparisons")["chunk-overlap-main"]

    assert comparison["confounded"] is True
    assert comparison["comparison_valid"] is False
    assert comparison["controlled_variables_match"] is False
    assert comparison["structurally_comparable"] is True
    blocking = [d for d in comparison["differences"] if d["severity"] == "blocking"]
    assert {d["category"] for d in blocking} >= {"prompt"}


def test_execution_failed_counterexample_is_present(walkthrough: Path) -> None:
    run = _records(walkthrough, "runs")["rerank-depth-main"]

    assert run["status"] == "invalid"
    assert run["failure"]["class"] == "data"
    assert run["abort_reason"]


def test_every_failed_chain_has_a_structured_diagnosis(walkthrough: Path) -> None:
    """終態只留一句 reason，回頭看時說不出當初排除過什麼。"""
    diagnoses = _records(walkthrough, "diagnoses")

    by_experiment = {d["experiment_id"]: d for d in diagnoses.values()}
    assert set(by_experiment) == {"rag-chunk-overlap", "rag-rerank-depth", "rag-query-rewrite"}
    for diagnosis in by_experiment.values():
        # 兩欄分開才讀得出哪些是已知、哪些是猜的。
        assert diagnosis["deterministic_facts"]
        assert all(fact["source_ref"] for fact in diagnosis["deterministic_facts"])
        assert diagnosis["hypotheses"]
        assert diagnosis["cheapest_next_test"]["distinguishes"]


def test_diagnoses_use_the_expected_failure_classes(walkthrough: Path) -> None:
    by_experiment = {d["experiment_id"]: d for d in _records(walkthrough, "diagnoses").values()}

    classes = {
        experiment_id: {h["failure_class"] for h in diagnosis["hypotheses"]}
        for experiment_id, diagnosis in by_experiment.items()
    }
    assert "confound" in classes["rag-chunk-overlap"]
    assert classes["rag-rerank-depth"] == {"data"}
    assert "insufficient_power" in classes["rag-query-rewrite"]


def test_inconclusive_counterexample_is_present(walkthrough: Path) -> None:
    """證據不足是正式終態，不是待辦，也不得被改寫成弱版本的成功。"""
    claim = _records(walkthrough, "claims")["query-rewrite-claim"]
    audit = _records(walkthrough, "audits")["query-rewrite-claim"]

    assert claim["status"] == "inconclusive"
    assert audit["final_verdict"] == "unsupported"
    assert audit["entailment"]["verdict"] == "not_entailed"
