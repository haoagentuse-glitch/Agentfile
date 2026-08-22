"""依凍結 analysis plan 產生 estimate 與 decision。"""

from __future__ import annotations

import random
from typing import Any


def evaluate_decision(
    interval: dict[str, Any] | None,
    estimate_scale: str,
    estimator_aligned: bool,
    rule: dict[str, Any],
) -> dict[str, Any]:
    """只套用凍結規則。缺值或規則不對齊時 fail closed。"""
    match rule["type"]:
        case "superiority":
            null = rule["null_value"]
            if interval is None:
                conclusion, reasons = "inconclusive", ["interval_missing"]
            elif interval["lower"] > null:
                conclusion, reasons = "superior", ["interval_above_null"]
            elif interval["upper"] < null:
                conclusion, reasons = "inferior", ["interval_below_null"]
            else:
                conclusion, reasons = "inconclusive", ["interval_crosses_null"]
        case "equivalence":
            margin = rule["equivalence_margin"]
            reasons: list[str] = []
            if interval is None:
                reasons.append("interval_missing")
            else:
                if estimate_scale != margin["scale"]:
                    reasons.append("scale_mismatch")
                if interval["confidence_level"] != margin["interval_confidence_level"]:
                    reasons.append("confidence_level_mismatch")
                if interval["method"] != margin["interval_method"]:
                    reasons.append("interval_method_mismatch")
            if not estimator_aligned:
                reasons.append("estimator_misaligned")
            if reasons:
                conclusion = "inconclusive"
            else:
                assert interval is not None
                if margin["boundary"] == "inclusive":
                    inside = margin["lower"] <= interval["lower"] and interval["upper"] <= margin["upper"]
                else:
                    inside = margin["lower"] < interval["lower"] and interval["upper"] < margin["upper"]
                conclusion = "equivalent" if inside else "inconclusive"
                reasons = ["interval_inside_margin" if inside else "interval_crosses_margin"]
        case unexpected:
            raise ValueError(f"不支援的 decision rule：{unexpected!r}")
    return {"rule_id": rule["id"], "conclusion": conclusion, "reason_codes": reasons}


def _percentile(values: list[float], alpha: float) -> tuple[float, float]:
    ordered = sorted(values)
    last = len(ordered) - 1
    return ordered[int(len(ordered) * alpha / 2)], ordered[min(last, int(len(ordered) * (1 - alpha / 2)))]


def joint_cluster_bootstrap(
    rows: list[dict[str, Any]],
    component_a: str,
    component_b: str,
    *,
    replicates: int,
    seed: int,
    confidence_level: float,
) -> dict[str, Any]:
    """同一次 cluster 重抽同時計算兩個 component 與其差。"""
    grouped: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        grouped.setdefault(str(row["cluster"]), {}).setdefault(str(row["component"]), []).append(float(row["value"]))
    clusters = sorted(grouped)
    if len(clusters) < 2:
        raise ValueError("joint_cluster_bootstrap 至少需要兩個 cluster")

    def mean(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    point_a = mean([v for cluster in clusters for v in grouped[cluster].get(component_a, [])])
    point_b = mean([v for cluster in clusters for v in grouped[cluster].get(component_b, [])])
    if point_a is None or point_b is None:
        raise ValueError("指定 component 沒有觀測值")

    rng = random.Random(seed)
    draws_a: list[float] = []
    draws_b: list[float] = []
    draws_diff: list[float] = []
    skipped = 0
    for _ in range(replicates):
        picked = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        draw_a = mean([v for cluster in picked for v in grouped[cluster].get(component_a, [])])
        draw_b = mean([v for cluster in picked for v in grouped[cluster].get(component_b, [])])
        if draw_a is None or draw_b is None:
            skipped += 1
            continue
        draws_a.append(draw_a)
        draws_b.append(draw_b)
        draws_diff.append(draw_a - draw_b)
    if not draws_diff:
        raise ValueError("所有 bootstrap replicate 都缺少 component")

    alpha = 1 - confidence_level
    lower, upper = _percentile(draws_diff, alpha)
    component_intervals = {}
    for name, point, draws in ((component_a, point_a, draws_a), (component_b, point_b, draws_b)):
        lo, hi = _percentile(draws, alpha)
        component_intervals[name] = {"point_estimate": point, "interval": {"lower": lo, "upper": hi}}
    return {
        "point_estimate": point_a - point_b,
        "interval": {"lower": lower, "upper": upper},
        "components": component_intervals,
        "clusters": len(clusters),
        "observations": len(rows),
        "skipped_replicates": skipped,
    }


def estimate_from_plan(
    estimand: dict[str, Any],
    estimator: dict[str, Any],
    rule: dict[str, Any],
    baseline_run: dict[str, Any],
    treatment_run: dict[str, Any],
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Exhaustive estimator dispatch。新增方法必須修改這個 match。"""
    method = estimator["type"]
    components: list[dict[str, Any]] = []
    interval: dict[str, Any] | None = None
    sample_size: dict[str, int] = {}
    metric = estimand["metric"]

    match method:
        case "difference":
            baseline = float(baseline_run["metrics"][metric])
            treatment = float(treatment_run["metrics"][metric])
            point = treatment - baseline
            components = [
                {"id": "baseline", "point_estimate": baseline},
                {"id": "treatment", "point_estimate": treatment},
            ]
        case "difference_in_differences":
            cells = estimator["cells"]
            values = {
                name: float((baseline_run if spec["run_role"] == "baseline" else treatment_run)["metrics"][spec["metric"]])
                for name, spec in cells.items()
            }
            point = (values["treatment_post"] - values["treatment_pre"]) - (
                values["control_post"] - values["control_pre"]
            )
            components = [{"id": name, "point_estimate": value} for name, value in values.items()]
            components.extend([
                {"id": "control_change", "point_estimate": values["control_post"] - values["control_pre"]},
                {"id": "treatment_change", "point_estimate": values["treatment_post"] - values["treatment_pre"]},
            ])
        case "joint_cluster_bootstrap":
            if rows is None:
                raise ValueError("joint_cluster_bootstrap 缺少逐筆資料")
            uncertainty = estimator["uncertainty"]
            calculated = joint_cluster_bootstrap(
                rows,
                estimator["component_a"],
                estimator["component_b"],
                replicates=uncertainty["replicates"],
                seed=uncertainty["seed"],
                confidence_level=uncertainty["confidence_level"],
            )
            point = calculated["point_estimate"]
            interval = {
                **calculated["interval"],
                "confidence_level": uncertainty["confidence_level"],
                "method": uncertainty["interval_method"],
            }
            components = [{"id": name, **value} for name, value in calculated["components"].items()]
            sample_size = {"observations": calculated["observations"], "clusters": calculated["clusters"]}
        case unexpected:
            raise ValueError(f"不支援的 estimator：{unexpected!r}")

    estimator_aligned = estimator["estimand_ref"] == estimand["id"]
    decision = evaluate_decision(interval, estimand["scale"], estimator_aligned, rule)
    return {
        "estimand_id": estimand["id"],
        "estimator_id": estimator["id"],
        "point_estimate": point,
        "interval": interval,
        "sample_size": sample_size,
        "method_ref": estimator["method_ref"],
        "component_estimates": components,
        "decision": decision,
    }
