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
            "compute_budget": {"pilot_max_minutes": 5, "pilot_max_samples": 100},
            "abort_rule": "guardrail 超標立即中止",
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
