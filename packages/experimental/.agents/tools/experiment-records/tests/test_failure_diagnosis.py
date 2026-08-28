"""失敗分類與最便宜下一步。

分類只有一份來源，deterministic_facts 與 hypotheses 分欄，
而且「能分辨假設」不能只是一句宣稱。
"""

from __future__ import annotations

import json
from pathlib import Path

from helpers import run_cli, valid_comparison, write_record

SCHEMAS = Path(__file__).resolve()
for _candidate in SCHEMAS.parents:
    if (_candidate / "records" / "experiments" / "schemas").is_dir():
        SCHEMAS = _candidate / "records" / "experiments" / "schemas"
        break

TAXONOMY = json.loads((SCHEMAS / "failure-taxonomy.schema.json").read_text(encoding="utf-8"))
FAILURE_CLASSES = TAXONOMY["$defs"]["failureClass"]["enum"]


def valid_diagnosis(**overrides: object) -> dict:
    data = {
        "diagnosis_id": "demo-diagnosis",
        "experiment_id": "demo-exp",
        "diagnosed_at": "2026-01-01T00:00:00Z",
        "subject": {"kind": "comparison", "ref": "records/experiments/comparisons/demo-comparison.json"},
        "deterministic_facts": [{
            "fact": "comparison 的 confounded 為 true",
            "source_ref": "records/experiments/comparisons/demo-comparison.json",
            "locator": "confounded",
        }],
        "hypotheses": [{
            "id": "h1",
            "failure_class": "confound",
            "statement": "評分器在兩次執行之間換版，提升可能整段來自評分器",
            "confidence": "high",
            "discriminating_observation": "用舊版評分器重跑 treatment，提升消失就是這個原因",
        }],
        "cheapest_next_test": {
            "description": "用舊版評分器重跑 treatment，不重建索引",
            "command": "python -m rag_lab pipeline run --stage main --judge answer-grader@4",
            "distinguishes": ["h1"],
            "estimated_cost": "約 50 分鐘",
        },
    }
    data.update(overrides)
    return data


def _project(project: Path, **overrides: object) -> Path:
    write_record(project, "comparisons", "demo-comparison", valid_comparison(confounded=True, comparison_valid=False))
    write_record(project, "diagnoses", "demo-diagnosis", valid_diagnosis(**overrides))
    return project


def test_taxonomy_has_exactly_the_seven_declared_classes() -> None:
    assert set(FAILURE_CLASSES) == {
        "execution", "data", "metric", "confound",
        "insufficient_power", "hypothesis_refuted", "scope_mismatch",
    }


def test_taxonomy_is_not_copied_into_other_schemas() -> None:
    """抄第二份的後果不是不同步而已——同一個失敗會被分成不同類，之後無法統計。"""
    copies = []
    for path in SCHEMAS.glob("*.json"):
        if path.name == "failure-taxonomy.schema.json":
            continue
        text = path.read_text(encoding="utf-8")
        if "hypothesis_refuted" in text and "failure-taxonomy.schema.json" not in text:
            copies.append(path.name)
    assert copies == []


def test_valid_diagnosis_passes(project: Path) -> None:
    result = run_cli("validate", str(_project(project)))

    assert result.returncode == 0, result.stdout + result.stderr


def test_every_failure_class_is_expressible(project: Path) -> None:
    hypotheses = [
        {"id": f"h{i}", "failure_class": failure_class, "statement": f"假設 {i}", "confidence": "low"}
        for i, failure_class in enumerate(FAILURE_CLASSES)
    ]
    excluded = [
        {"failure_class": failure_class, "reason": "已由紀錄排除"}
        for failure_class in ("execution", "data", "metric", "confound", "insufficient_power")
    ]
    result = run_cli("validate", str(_project(
        project,
        hypotheses=hypotheses,
        excluded_classes=excluded,
        cheapest_next_test={"description": "掃一輪", "distinguishes": [h["id"] for h in hypotheses]},
    )))

    assert result.returncode == 0, result.stdout + result.stderr


def test_unknown_failure_class_is_rejected(project: Path) -> None:
    result = run_cli("validate", str(_project(project, hypotheses=[{
        "id": "h1", "failure_class": "看起來怪怪的", "statement": "隨便", "confidence": "low",
    }])))

    assert result.returncode == 1
    assert "failure_class" in result.stdout


def test_deterministic_fact_requires_a_source(project: Path) -> None:
    """說不出來源的就是推測，該放 hypotheses。"""
    result = run_cli("validate", str(_project(project, deterministic_facts=[
        {"fact": "大概是評分器的問題"}
    ])))

    assert result.returncode == 1
    assert "source_ref" in result.stdout


def test_deterministic_fact_source_must_resolve(project: Path) -> None:
    result = run_cli("validate", str(_project(project, deterministic_facts=[
        {"fact": "某個事實", "source_ref": "records/experiments/runs/missing.json"}
    ])))

    assert result.returncode == 1
    assert "deterministic_facts.0.source_ref" in result.stdout


def test_next_test_must_distinguish_a_real_hypothesis(project: Path) -> None:
    """「能分辨假設」不能只是一句宣稱。"""
    result = run_cli("validate", str(_project(project, cheapest_next_test={
        "description": "再跑一次", "distinguishes": ["h9"],
    })))

    assert result.returncode == 1
    assert "指向不存在的 hypotheses.id 'h9'" in result.stdout


def test_next_test_cannot_distinguish_nothing(project: Path) -> None:
    """不能分辨假設的測試不算下一步，只是再跑一次。"""
    result = run_cli("validate", str(_project(project, cheapest_next_test={
        "description": "再跑一次", "distinguishes": [],
    })))

    assert result.returncode == 1
    assert "distinguishes" in result.stdout


def test_hypothesis_refuted_needs_the_other_classes_excluded(project: Path) -> None:
    """hypothesis_refuted 是正式結論，不是最後的兜底選項。"""
    result = run_cli("validate", str(_project(
        project,
        hypotheses=[{
            "id": "h1", "failure_class": "hypothesis_refuted",
            "statement": "假說就是錯的", "confidence": "medium",
        }],
    )))

    assert result.returncode == 1
    assert "判 hypothesis_refuted 之前必須先排除" in result.stdout


def test_hypothesis_refuted_with_exclusions_passes(project: Path) -> None:
    result = run_cli("validate", str(_project(
        project,
        hypotheses=[{
            "id": "h1", "failure_class": "hypothesis_refuted",
            "statement": "條件都守住了，效應就是不存在", "confidence": "medium",
        }],
        excluded_classes=[
            {"failure_class": "execution", "reason": "所有 run 的 status 都是 completed"},
            {"failure_class": "data", "reason": "資料雜湊與 Contract 鎖定當下一致"},
            {"failure_class": "metric", "reason": "兩邊 metric_definitions 相同"},
            {"failure_class": "confound", "reason": "comparison 的 controlled_variables_match 為 true"},
            {"failure_class": "insufficient_power", "reason": "三次複現的變異遠小於觀察到的差距"},
        ],
    )))

    assert result.returncode == 0, result.stdout + result.stderr


def test_duplicate_hypothesis_ids_are_rejected(project: Path) -> None:
    result = run_cli("validate", str(_project(project, hypotheses=[
        {"id": "h1", "failure_class": "confound", "statement": "第一個", "confidence": "low"},
        {"id": "h1", "failure_class": "data", "statement": "第二個", "confidence": "low"},
    ])))

    assert result.returncode == 1
    assert "hypotheses ID 重複：h1" in result.stdout


def test_subject_must_point_at_an_existing_record(project: Path) -> None:
    """診斷要指到具體紀錄，不是「這個實驗好像怪怪的」。"""
    result = run_cli("validate", str(_project(project, subject={
        "kind": "run", "ref": "records/experiments/runs/missing.json",
    })))

    assert result.returncode == 1
    assert "subject.ref" in result.stdout
