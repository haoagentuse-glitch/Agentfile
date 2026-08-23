"""compare_runs.py 的實際輸出必須通過 comparison-result schema。

這是生產者與驗證器之間的端到端契約測試。schema 改了但產生器沒跟上，
或產生器多寫了一個 schema 不認得的欄位，都會在這裡失敗，而不是等到有人
把不合法的 comparison 存進 records/ 才發現。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from helpers import run_cli

BASELINE_CONFIG = {"dataset": "corpus-a", "model": "embed-v1", "top_k": 5, "seed": 42}
METRIC_DEFINITIONS = {"recall_at_10": "records/experiments/metrics/recall_at_10.json"}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_record(run_id: str, **overrides: object) -> dict:
    record = {
        "run_id": run_id,
        "experiment_id": "smoke-exp",
        "experiment_type": "rag",
        "created_at": "2026-01-01T00:00:00Z",
        "config_hash": f"sha256:{run_id}",
        "config_ref": "records/experiments/configs/baseline.json",
        "schema_version": "1",
        "status": "completed",
        "seed": 42,
        "stage": "pilot",
        "baseline_run": None,
        "metric_definitions": dict(METRIC_DEFINITIONS),
        "metrics": {"recall_at_10": 0.62},
    }
    record.update(overrides)
    return record


@pytest.fixture
def scenario(project: Path):
    """建立一個可以直接餵給 compare_runs.py 的最小專案。"""
    root = project / "records" / "experiments"

    def build(treatment_config: dict, **treatment_overrides: object) -> Path:
        _write(root / "configs" / "baseline.json", BASELINE_CONFIG)
        _write(root / "configs" / "treatment.json", treatment_config)
        _write(root / "definitions" / "smoke-exp.json", {
            "experiment_id": "smoke-exp",
            "question": "top_k 提高是否讓 recall 提升？",
            "hypothesis": "提高 top_k 會提升 recall",
            "baseline": {"description": "b", "config_ref": "records/experiments/configs/baseline.json"},
            "treatment": {
                "description": "t",
                "config_ref": "records/experiments/configs/treatment.json",
                "variable": "top_k",
            },
            "controlled_variables": ["dataset", "model", "seed"],
            "primary_metric": "recall_at_10",
            "decision_rule": "recall 提升至少 0.05 視為成功",
            "analysis_plan": {
                "estimands": [{"id": "effect.primary", "metric": "recall_at_10", "population": "固定評估集", "conditions": {"baseline": "baseline", "treatment": "treatment"}, "scale": "raw", "summary_measure": "difference", "orientation": "treatment_minus_baseline"}],
                "estimators": [{"id": "estimator.primary", "estimand_ref": "effect.primary", "type": "difference", "method_ref": "arithmetic-difference"}],
                "decision_rules": [{"id": "decision.primary", "estimand_ref": "effect.primary", "type": "superiority", "null_value": 0.0}]
            },
            "compute_budget": {"pilot_max_minutes": 5, "pilot_max_samples": 100},
            "abort_rule": "guardrail 超標立即中止",
            "evidence_policy": {"eligible_run_stages": ["pilot", "main", "replication"]},
            "status": "draft",
            "created_at": "2026-01-01T00:00:00Z",
        })
        _write(root / "runs" / "smoke-baseline.json", _run_record("smoke-baseline"))
        _write(root / "runs" / "smoke-treatment.json", _run_record(
            "smoke-treatment",
            config_ref="records/experiments/configs/treatment.json",
            baseline_run="smoke-baseline",
            metrics={"recall_at_10": 0.71},
            **treatment_overrides,
        ))
        return project

    return build


def _compare(project: Path) -> tuple[subprocess.CompletedProcess[str], dict | None]:
    output = project / "records" / "experiments" / "comparisons" / "smoke.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run_cli(
        "compare-runs",
        "records/experiments/runs/smoke-baseline.json",
        "records/experiments/runs/smoke-treatment.json",
        "--output",
        str(output),
        cwd=project,
    )
    written = json.loads(output.read_text(encoding="utf-8")) if output.is_file() else None
    return result, written


def test_clean_comparison_output_validates(scenario) -> None:
    project = scenario({"dataset": "corpus-a", "model": "embed-v1", "top_k": 10, "seed": 42})

    compare, written = _compare(project)

    assert compare.returncode == 0, compare.stdout + compare.stderr
    assert written is not None
    assert written["structurally_comparable"] is True
    assert written["controlled_variables_match"] is True
    assert written["comparison_valid"] is True
    assert written["evidence_eligible"] is True
    assert written["confounded"] is False

    validate = run_cli("validate", str(project))
    assert validate.returncode == 0, validate.stdout + validate.stderr


def test_declared_variable_appears_as_an_informational_difference(scenario) -> None:
    project = scenario({"dataset": "corpus-a", "model": "embed-v1", "top_k": 10, "seed": 42})

    _, written = _compare(project)

    declared = [d for d in written["differences"] if d["declared"]]
    assert [d["key"] for d in declared] == ["top_k"]
    assert declared[0]["severity"] == "informational"


def test_confounded_output_names_the_blocking_difference(scenario) -> None:
    """控制條件被動到就是阻斷級差異，而且要說得出是哪一類、哪一個欄位。"""
    project = scenario({"dataset": "corpus-b", "model": "embed-v1", "top_k": 10, "seed": 42})

    compare, written = _compare(project)

    assert compare.returncode == 1
    assert written["confounded"] is True
    assert written["controlled_variables_match"] is False
    assert written["comparison_valid"] is False
    blocking = {d["key"]: d for d in written["differences"] if d["severity"] == "blocking"}
    assert "dataset" in blocking
    assert blocking["dataset"]["category"] == "data"

    # 整個 project 會被判不合法——controlled_variable 真的不同，Contract 本身就不可識別。
    # 這裡只檢查產出的 comparison record 本身合乎 schema。
    comparison_path = project / "records" / "experiments" / "comparisons" / "smoke.json"
    validate = run_cli("validate", str(comparison_path))
    assert validate.returncode == 0, validate.stdout + validate.stderr


def test_undeclared_difference_is_categorized(scenario) -> None:
    project = scenario({
        "dataset": "corpus-a", "model": "embed-v1", "top_k": 10, "seed": 42,
        "judge_prompt": "v2",
    })

    _, written = _compare(project)

    blocking = {d["key"]: d for d in written["differences"] if d["severity"] == "blocking"}
    assert "judge_prompt" in blocking
    assert blocking["judge_prompt"]["category"] == "prompt"


def test_inconsistent_metric_definition_makes_it_structurally_incomparable(scenario) -> None:
    """兩邊用不同算法算同名指標，就沒有共同基準——這是 invalid 但不是 confounded。"""
    project = scenario(
        {"dataset": "corpus-a", "model": "embed-v1", "top_k": 10, "seed": 42},
        metric_definitions={"recall_at_10": "records/experiments/metrics/recall_at_10_v2.json"},
    )

    compare, written = _compare(project)

    assert compare.returncode == 1
    assert written["structurally_comparable"] is False
    assert written["confounded"] is False
    assert written["comparison_valid"] is False
    assert written["metrics"]["recall_at_10"]["computed"] is False

    validate = run_cli("validate", str(project))
    assert validate.returncode == 0, validate.stdout + validate.stderr


def test_diagnostic_suggestions_start_empty(scenario) -> None:
    """程式不產生建議。這欄留給 agent 填，且永遠不影響 validity 欄位。"""
    project = scenario({"dataset": "corpus-a", "model": "embed-v1", "top_k": 10, "seed": 42})

    _, written = _compare(project)

    assert written["diagnostic_suggestions"] == []


def test_diagnostic_stage_computes_numbers_but_is_not_formal_evidence(scenario) -> None:
    project = scenario(
        {"dataset": "corpus-a", "model": "embed-v1", "top_k": 10, "seed": 42},
        stage="diagnostic",
    )

    compare, written = _compare(project)

    assert compare.returncode == 1
    assert written["comparison_valid"] is True
    assert written["metrics"]["recall_at_10"]["computed"] is True
    assert written["evidence_eligible"] is False
    assert any("diagnostic" in reason for reason in written["evidence_reasons"])


def _freeze_bootstrap_estimator(project: Path) -> None:
    path = project / "records" / "experiments" / "definitions" / "smoke-exp.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    contract["analysis_plan"]["estimators"] = [{
        "id": "estimator.primary",
        "estimand_ref": "effect.primary",
        "type": "joint_cluster_bootstrap",
        "method_ref": "joint-cluster-bootstrap@1",
        "component_a": "topic",
        "component_b": "exact",
        "uncertainty": {
            "confidence_level": 0.95,
            "interval_method": "percentile",
            "resampling_unit": "query_id",
            "replicates": 500,
            "seed": 1729,
            "method_reference": "https://doi.org/10.1111/j.1467-9868.2007.00593.x",
        },
    }]
    _write(path, contract)


def _write_per_question(project: Path, run_id: str, offset: float) -> str:
    """逐筆結果 JSONL：8 個 cluster，兩個分層，每題一列。"""
    ref = f"records/experiments/per-question/{run_id}.jsonl"
    path = project / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(8):
        lines.append({"case_id": f"topic-{i}", "cluster": f"v{i}", "component": "topic", "value": 0.5 + 0.05 * i + offset})
        lines.append({"case_id": f"exact-{i}", "cluster": f"v{i}", "component": "exact", "value": 0.6 + 0.01 * i + offset * 0.5})
    path.write_text("\n".join(json.dumps(line, ensure_ascii=False) for line in lines) + "\n", encoding="utf-8")
    return ref


def _attach_per_question(project: Path) -> None:
    for run_id, offset in (("smoke-baseline", 0.0), ("smoke-treatment", 0.08)):
        ref = _write_per_question(project, run_id, offset)
        run_path = project / "records" / "experiments" / "runs" / f"{run_id}.json"
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["per_question_ref"] = ref
        run["per_question_metric"] = "recall_at_10"
        _write(run_path, run)


def test_bootstrap_estimand_without_row_data_says_why_there_is_no_estimate(scenario) -> None:
    """run envelope 只有彙總指標，重抽 cluster 需要逐筆資料。缺輸入不估計，但不得靜默略過。"""
    project = scenario({"dataset": "corpus-a", "model": "embed-v1", "top_k": 10, "seed": 42})
    _freeze_bootstrap_estimator(project)

    _, written = _compare(project)

    assert written["estimates"] == []
    assert any("per_question_ref" in note for note in written["notes"])


def test_bootstrap_estimand_with_row_data_persists_interval_and_decision(scenario) -> None:
    """有逐筆資料就走凍結的重抽設定，區間與判定一起寫進紀錄。"""
    project = scenario({"dataset": "corpus-a", "model": "embed-v1", "top_k": 10, "seed": 42})
    _freeze_bootstrap_estimator(project)
    _attach_per_question(project)

    compare, written = _compare(project)

    assert compare.returncode == 0, compare.stdout + compare.stderr
    [estimate] = written["estimates"]
    assert estimate["estimand_id"] == "effect.primary"
    assert estimate["method_ref"] == "joint-cluster-bootstrap@1"
    assert estimate["interval"]["confidence_level"] == 0.95
    assert estimate["interval"]["method"] == "percentile"
    assert estimate["interval"]["lower"] <= estimate["point_estimate"] <= estimate["interval"]["upper"]
    assert estimate["sample_size"] == {"observations": 16, "clusters": 8}
    assert {item["id"] for item in estimate["component_estimates"]} == {"topic", "exact"}
    # 區間完全在 null value 之上，才判 superior；這組資料就是這種情況。
    assert estimate["decision"]["conclusion"] == "superior"
    assert estimate["decision"]["reason_codes"] == ["interval_above_null"]

    validate = run_cli("validate", str(project))
    assert validate.returncode == 0, validate.stdout + validate.stderr


def test_mismatched_case_sets_block_the_estimate_instead_of_dropping_rows(scenario) -> None:
    """少一題就不是配對比較。缺題不得被靜默丟掉。"""
    project = scenario({"dataset": "corpus-a", "model": "embed-v1", "top_k": 10, "seed": 42})
    _freeze_bootstrap_estimator(project)
    _attach_per_question(project)
    path = project / "records" / "experiments" / "per-question" / "smoke-treatment.jsonl"
    kept = path.read_text(encoding="utf-8").splitlines()[:-1]
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")

    _, written = _compare(project)

    assert written["estimates"] == []
    assert any("題目集合不一致" in note for note in written["notes"])
