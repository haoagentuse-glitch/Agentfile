from __future__ import annotations

import pytest
from experiment_records.comparison_analysis import (
    estimate_from_plan,
    evaluate_decision,
    joint_cluster_bootstrap,
)


def _estimand(summary: str = "difference") -> dict:
    return {
        "id": "effect.primary",
        "metric": "score",
        "scale": "raw",
        "summary_measure": summary,
    }


def _rule() -> dict:
    return {"id": "decision.primary", "type": "superiority", "null_value": 0.0}


def test_difference_persists_components_and_numeric_orientation() -> None:
    estimate = estimate_from_plan(
        _estimand(),
        {
            "id": "estimator.primary",
            "estimand_ref": "effect.primary",
            "type": "difference",
            "method_ref": "arithmetic-difference@1",
        },
        _rule(),
        {"metrics": {"score": 0.4}},
        {"metrics": {"score": 0.7}},
    )
    assert estimate["point_estimate"] == pytest.approx(0.3)
    assert [item["id"] for item in estimate["component_estimates"]] == ["baseline", "treatment"]
    assert estimate["decision"]["conclusion"] == "inconclusive"


def test_difference_in_differences_persists_four_cells_and_changes() -> None:
    estimator = {
        "id": "estimator.did",
        "estimand_ref": "effect.primary",
        "type": "difference_in_differences",
        "method_ref": "did@1",
        "cells": {
            "control_pre": {"run_role": "baseline", "metric": "control_pre"},
            "control_post": {"run_role": "baseline", "metric": "control_post"},
            "treatment_pre": {"run_role": "treatment", "metric": "treatment_pre"},
            "treatment_post": {"run_role": "treatment", "metric": "treatment_post"},
        },
    }
    estimate = estimate_from_plan(
        _estimand("difference_in_differences"),
        estimator,
        _rule(),
        {"metrics": {"control_pre": 0.61, "control_post": 0.63}},
        {"metrics": {"treatment_pre": 0.60, "treatment_post": 0.65}},
    )
    assert estimate["point_estimate"] == pytest.approx(0.03)
    assert {item["id"] for item in estimate["component_estimates"]} == {
        "control_pre", "control_post", "treatment_pre", "treatment_post",
        "control_change", "treatment_change",
    }


def test_joint_cluster_bootstrap_uses_one_draw_for_both_components() -> None:
    # 每個 cluster 的兩個 component 差固定是 -1，但各 component 的水準隨 cluster 變動。
    # 同一次抽樣算兩個 component 時，差的分佈必然退化成單點；各自獨立抽樣則不會。
    # 這組資料把「有沒有保留 component 間的 bootstrap dependence」變成可判定的差異。
    rows = [
        {"cluster": f"c{i}", "component": "topic", "value": float(i)}
        for i in range(10)
    ] + [
        {"cluster": f"c{i}", "component": "exact", "value": float(i) + 1.0}
        for i in range(10)
    ]
    result = joint_cluster_bootstrap(
        rows, "topic", "exact", replicates=400, seed=3, confidence_level=0.95
    )
    assert result["point_estimate"] == pytest.approx(-1.0)
    assert result["interval"]["lower"] == pytest.approx(-1.0)
    assert result["interval"]["upper"] == pytest.approx(-1.0)
    # component 自己的區間必須有寬度，否則上面的零寬度只是因為根本沒重抽。
    topic = result["components"]["topic"]["interval"]
    assert topic["upper"] - topic["lower"] > 0
    assert result["clusters"] == 10
    assert result["observations"] == 20


def test_interval_crossing_equivalence_margin_is_inconclusive() -> None:
    rule = {
        "id": "decision.eq",
        "type": "equivalence",
        "equivalence_margin": {
            "lower": -0.05,
            "upper": 0.05,
            "scale": "raw",
            "interval_confidence_level": 0.95,
            "interval_method": "percentile",
            "boundary": "exclusive",
        },
    }
    interval = {"lower": -0.02, "upper": 0.06, "confidence_level": 0.95, "method": "percentile"}
    decision = evaluate_decision(interval, "raw", True, rule)
    assert decision["conclusion"] == "inconclusive"
    assert decision["reason_codes"] == ["interval_crosses_margin"]


def test_interval_inside_equivalence_margin_is_equivalent() -> None:
    rule = {
        "id": "decision.eq",
        "type": "equivalence",
        "equivalence_margin": {
            "lower": -0.05,
            "upper": 0.05,
            "scale": "raw",
            "interval_confidence_level": 0.95,
            "interval_method": "percentile",
            "boundary": "exclusive",
        },
    }
    interval = {"lower": -0.02, "upper": 0.04, "confidence_level": 0.95, "method": "percentile"}
    decision = evaluate_decision(interval, "raw", True, rule)
    assert decision["conclusion"] == "equivalent"
    assert decision["reason_codes"] == ["interval_inside_margin"]


def test_estimator_pointing_at_another_estimand_cannot_conclude_equivalence() -> None:
    rule = {
        "id": "decision.eq",
        "type": "equivalence",
        "equivalence_margin": {
            "lower": -0.5,
            "upper": 0.5,
            "scale": "raw",
            "interval_confidence_level": 0.95,
            "interval_method": "percentile",
            "boundary": "exclusive",
        },
    }
    interval = {"lower": -0.02, "upper": 0.04, "confidence_level": 0.95, "method": "percentile"}
    decision = evaluate_decision(interval, "raw", False, rule)
    assert decision["conclusion"] == "inconclusive"
    assert decision["reason_codes"] == ["estimator_misaligned"]


def test_unknown_estimator_fails_closed() -> None:
    with pytest.raises(ValueError, match="不支援的 estimator"):
        estimate_from_plan(
            _estimand(),
            {"id": "x", "estimand_ref": "effect.primary", "type": "plugin", "method_ref": "x"},
            _rule(),
            {"metrics": {"score": 0.4}},
            {"metrics": {"score": 0.7}},
        )
