#!/usr/bin/env python3
"""比較兩個 run，先判可比較性、確認的話才算指標差異。deterministic，不靠 LLM 判斷。

用法：
  python3 compare_runs.py <run_a.json> <run_b.json> [--contract PATH] [--metrics-dir DIR] [--output PATH] [--json]

只用標準函式庫。流程：
  1. 載入兩個 Run Envelope，確認屬於同一個 experiment。
  2. 載入對應的 Experiment Contract，取得宣告的實驗變因與控制條件。
  3. 用 config_ref 載入兩邊實際用的設定，逐欄位比對：
     相同條件 / 已宣告差異（declared variable）/ 未預期差異。
  4. 有未預期差異、或宣告要控制的欄位實際卻不同、或宣告的變因根本沒變 → confounded。
  5. metric 層級另外檢查兩邊是不是用同一套 metric definition 算出來的——不一致的
     metric 個別跳過，不影響其他 metric。一個都對不上就是 structurally_comparable=false。

三個判斷刻意分開，因為它們問的是不同問題：
  structurally_comparable    兩邊在講同一件事嗎（有沒有共同基準）
  controlled_variables_match 除了宣告的變因，其他條件真的一樣嗎
  confounded                 差異嚴重到不能歸因嗎
comparison_valid 才是綜合結論：非 confounded 且結構可比較。三者都由程式算，
不接受 LLM 直接決定；agent 的解釋與建議只能進 diagnostic_suggestions。

exit code：0 = 可引用，1 = 不可引用（confounded 或沒有共同基準）。
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
from typing import Any

from experiment_records.comparison_analysis import estimate_from_plan
from experiment_records.evidence_policy import evaluate_evidence_policy


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_records_root(start: Path) -> Path:
    """從 start 往上找到含 records/experiments/schemas 的目錄，回傳 records/experiments/ 本身。"""
    for candidate in [start, *start.parents]:
        probe = candidate / "records" / "experiments"
        if (probe / "schemas").is_dir():
            return probe
    raise FileNotFoundError("找不到 records/experiments/——確認在專案內執行")


def check_schema(instance: dict, schema: dict, path: str, results: list[tuple[str, str]]) -> None:
    """遞迴檢查 required 欄位與 enum 限制，複用 experiment-lint 的作法。"""
    for key in schema.get("required", []):
        label = f"{path}.{key}" if path else key
        if key not in instance or instance[key] in (None, "", []):
            results.append(("ERROR", f"missing required field: {label}"))

    for key, subschema in schema.get("properties", {}).items():
        if key not in instance:
            continue
        value = instance[key]
        label = f"{path}.{key}" if path else key
        enum = subschema.get("enum")
        if enum is not None and value not in enum:
            results.append(("ERROR", f"{label} = {value!r} not in allowed values {enum}"))
        if subschema.get("type") == "object" and isinstance(value, dict):
            check_schema(value, subschema, label, results)


# 固定要檢查的維度：欄位候選名稱（設定檔命名習慣不同專案不一樣，這裡列常見別名；
# 專案用了別的名稱就把它加進 Contract 的 controlled_variables，一樣會被抓到）
NAMED_DIMENSIONS: dict[str, list[str]] = {
    "dataset": ["dataset", "dataset_name", "dataset_version"],
    "evaluation_set": ["evaluation_set", "eval_set", "eval_dataset"],
    "model": ["model", "model_name"],
}

# 差異分類：把設定欄位名歸到 config／data／model／prompt／evaluator，讓「差在哪一類」
# 可以直接讀出來，不必每個下游各自重新判斷欄位名的意思。對不上就是 unknown——
# 猜錯分類比不分類更糟。
DIFFERENCE_CATEGORIES: dict[str, tuple[str, ...]] = {
    "data": ("dataset", "corpus", "eval_set", "evaluation_set", "eval_dataset", "sample", "split"),
    "model": ("model", "embedding", "retriever", "reranker", "generator"),
    "prompt": ("prompt", "instruction", "system_message", "temperature"),
    "evaluator": ("evaluator", "judge", "scorer", "metric_impl"),
}


def categorize_difference(key: str) -> str:
    lowered = key.lower()
    for category, markers in DIFFERENCE_CATEGORIES.items():
        if any(marker in lowered for marker in markers):
            return category
    return "config"


def resolve_config(run: dict, records_root: Path) -> dict | None:
    """config_ref 一律相對 project root 解析，跟 experiment_records 的 ref 規則一致。

    兩邊用不同慣例的話，同一份 record 會出現「驗證得過但比較不了」的狀況。
    """
    ref = run.get("config_ref")
    if not ref:
        return None
    project_root = records_root.parent.parent
    candidate = (project_root / ref).resolve()
    if not candidate.is_file() or project_root.resolve() not in candidate.parents:
        return None
    return load_json(candidate)


def diff_dimension(name: str, candidates: list[str], cfg_a: dict, cfg_b: dict) -> dict[str, Any] | None:
    for key in candidates:
        if key in cfg_a or key in cfg_b:
            va, vb = cfg_a.get(key, "<absent>"), cfg_b.get(key, "<absent>")
            return {"status": "PASS" if va == vb else "DIFF", "run_a_value": va, "run_b_value": vb, "_key": key}
    return None


def resolve_roles(run_a: dict, run_b: dict) -> tuple[dict, dict]:
    """回傳 (baseline_run, treatment_run)。用 baseline_run 欄位判斷；判斷不出來就假設
    傳入順序就是 (baseline, treatment)。"""
    if run_a.get("baseline_run") is None and run_b.get("baseline_run") == run_a["run_id"]:
        return run_a, run_b
    if run_b.get("baseline_run") is None and run_a.get("baseline_run") == run_b["run_id"]:
        return run_b, run_a
    return run_a, run_b


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_a")
    ap.add_argument("run_b")
    ap.add_argument("--contract")
    ap.add_argument("--metrics-dir")
    ap.add_argument("--output")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    run_a_path = Path(args.run_a).resolve()
    run_b_path = Path(args.run_b).resolve()
    run_a = load_json(run_a_path)
    run_b = load_json(run_b_path)

    records_root = find_records_root(run_a_path.parent)
    schemas = records_root / "schemas"
    envelope_schema = load_json(schemas / "run-envelope.schema.json")

    lint: list[tuple[str, str]] = []
    check_schema(run_a, envelope_schema, f"run_a({run_a.get('run_id')})", lint)
    check_schema(run_b, envelope_schema, f"run_b({run_b.get('run_id')})", lint)
    if run_a.get("experiment_id") != run_b.get("experiment_id"):
        lint.append(("ERROR", f"run_a.experiment_id={run_a.get('experiment_id')!r} != run_b.experiment_id={run_b.get('experiment_id')!r}——不同 experiment 無法比較"))
    errors = [m for lvl, m in lint if lvl == "ERROR"]
    if errors:
        for lvl, msg in lint:
            print(f"{lvl:5s} {msg}")
        print(f"\n{len(errors)} error(s). Cannot compare.")
        return 2

    experiment_id = run_a["experiment_id"]
    contract_path = Path(args.contract) if args.contract else records_root / "definitions" / f"{experiment_id}.json"
    contract = load_json(contract_path) if contract_path.is_file() else None

    controlled_variables: list[str] = contract.get("controlled_variables", []) if contract else []
    declared_variable_name = contract.get("treatment", {}).get("variable") if contract else None

    baseline_run, treatment_run = resolve_roles(run_a, run_b)
    evidence = evaluate_evidence_policy(contract or {}, [baseline_run, treatment_run])
    cfg_a = resolve_config(baseline_run, records_root)
    cfg_b = resolve_config(treatment_run, records_root)

    dimensions: dict[str, Any] = {}
    other_differences: list[dict[str, Any]] = []
    differences: list[dict[str, Any]] = []
    declared_variable: dict[str, Any] = {"name": declared_variable_name, "run_a_value": None, "run_b_value": None, "changed": False}
    notes: list[str] = []

    if cfg_a is None or cfg_b is None:
        notes.append("baseline 或 treatment 的 config_ref 缺失或指到不存在的檔案，只能用 config_hash 判斷有沒有差異，無法逐欄位比對")
        for name in NAMED_DIMENSIONS:
            dimensions[name] = {"status": "SKIPPED"}
        for name in controlled_variables:
            dimensions[name] = {"status": "SKIPPED"}
        confounded = baseline_run.get("config_hash") != treatment_run.get("config_hash")
        confounded_reasons = ["config_ref 缺失，config_hash 不同但無法指出差在哪個欄位"] if confounded else []
        if confounded:
            differences.append({
                "category": "unknown",
                "key": "config_hash",
                "run_a_value": baseline_run.get("config_hash"),
                "run_b_value": treatment_run.get("config_hash"),
                "severity": "blocking",
                "declared": False,
            })
        # 逐欄位比不了就不知道控制條件有沒有守住。「不知道」不等於「相同」。
        controlled_variables_match = False
    else:
        accounted_keys: set[str] = set()
        for name, candidates in NAMED_DIMENSIONS.items():
            result = diff_dimension(name, candidates, cfg_a, cfg_b)
            if result is None:
                dimensions[name] = {"status": "SKIPPED"}
                continue
            accounted_keys.add(result.pop("_key"))
            dimensions[name] = result

        for name in controlled_variables:
            if name in dimensions:
                continue
            va, vb = cfg_a.get(name, "<absent>"), cfg_b.get(name, "<absent>")
            dimensions[name] = {"status": "PASS" if va == vb else "DIFF", "run_a_value": va, "run_b_value": vb}
            accounted_keys.add(name)

        if declared_variable_name:
            va = cfg_a.get(declared_variable_name, "<absent>")
            vb = cfg_b.get(declared_variable_name, "<absent>")
            declared_variable = {"name": declared_variable_name, "run_a_value": va, "run_b_value": vb, "changed": va != vb}
            accounted_keys.add(declared_variable_name)

        all_keys = set(cfg_a) | set(cfg_b)
        for key in sorted(all_keys - accounted_keys):
            va, vb = cfg_a.get(key, "<absent>"), cfg_b.get(key, "<absent>")
            if va != vb:
                other_differences.append({"key": key, "run_a_value": va, "run_b_value": vb})

        confounded_reasons = []
        for name, d in dimensions.items():
            if d["status"] == "DIFF":
                confounded_reasons.append(f"維度 '{name}' 應該一致卻不同：{d['run_a_value']!r} vs {d['run_b_value']!r}")
                differences.append({
                    "category": categorize_difference(name),
                    "key": name,
                    "run_a_value": d["run_a_value"],
                    "run_b_value": d["run_b_value"],
                    "severity": "blocking",
                    "declared": False,
                })
        if other_differences:
            confounded_reasons.append(f"{len(other_differences)} 個未宣告的欄位差異：{', '.join(d['key'] for d in other_differences)}")
            for d in other_differences:
                differences.append({
                    "category": categorize_difference(d["key"]),
                    "key": d["key"],
                    "run_a_value": d["run_a_value"],
                    "run_b_value": d["run_b_value"],
                    "severity": "blocking",
                    "declared": False,
                })
        if declared_variable_name and not declared_variable["changed"]:
            confounded_reasons.append(f"宣告的實驗變因 '{declared_variable_name}' 實際上兩邊相同，沒有有效的處理效應可以歸因")
        elif declared_variable_name:
            # 宣告的變因本身當然不同——那正是實驗要測的東西，列出來但不是阻斷級。
            differences.append({
                "category": categorize_difference(declared_variable_name),
                "key": declared_variable_name,
                "run_a_value": declared_variable["run_a_value"],
                "run_b_value": declared_variable["run_b_value"],
                "severity": "informational",
                "declared": True,
            })
        confounded = bool(confounded_reasons)
        controlled_variables_match = not any(d["severity"] == "blocking" for d in differences)

    # metric 層級先判 definition 是否一致——這是「兩邊在講同一件事嗎」，
    # 跟「條件有沒有守住」是兩個獨立問題，必須先算完才能決定整體 comparison_valid。
    metric_names = sorted(set(baseline_run.get("metrics", {})) | set(treatment_run.get("metrics", {})))
    if contract:
        metric_names = sorted(set(metric_names) | {contract.get("primary_metric")} | set(contract.get("secondary_metrics", [])) - {None})

    shared: dict[str, bool] = {}
    for name in metric_names:
        def_a = baseline_run.get("metric_definitions", {}).get(name)
        def_b = treatment_run.get("metric_definitions", {}).get(name)
        definition_consistent = True
        if def_a is not None and def_b is not None and def_a != def_b:
            definition_consistent = False
            notes.append(f"metric '{name}' 的定義不一致：baseline 用 {def_a!r}，treatment 用 {def_b!r}")
            differences.append({
                "category": "evaluator",
                "key": f"metric_definitions.{name}",
                "run_a_value": def_a,
                "run_b_value": def_b,
                "severity": "blocking",
                "declared": False,
            })
        elif def_a is None or def_b is None:
            notes.append(f"metric '{name}' 至少一邊沒記錄 metric_definitions，無法驗證是否同一套算法")
        shared[name] = definition_consistent

    # 沒有任何一個指標兩邊都有、且用同一套定義算出來 → 這次比較沒有共同基準。
    # 這是 invalid 但不是 confounded：不是條件沒守住，是根本沒有可對照的量。
    structurally_comparable = any(
        consistent
        and name in baseline_run.get("metrics", {})
        and name in treatment_run.get("metrics", {})
        for name, consistent in shared.items()
    )
    if not structurally_comparable:
        notes.append("沒有任何指標在兩邊都存在且定義一致，這次比較沒有共同基準")

    comparison_valid = (not confounded) and structurally_comparable

    metrics_out: dict[str, Any] = {}
    for name in metric_names:
        definition_consistent = shared[name]
        can_compute = comparison_valid and definition_consistent and name in baseline_run.get("metrics", {}) and name in treatment_run.get("metrics", {})
        entry: dict[str, Any] = {"definition_consistent": definition_consistent, "computed": can_compute}
        if can_compute:
            b = baseline_run["metrics"][name]
            t = treatment_run["metrics"][name]
            entry["baseline"] = b
            entry["treatment"] = t
            entry["absolute_diff"] = t - b
            entry["relative_diff"] = (t - b) / b if b else None
        else:
            entry["baseline"] = entry["treatment"] = entry["absolute_diff"] = entry["relative_diff"] = None
        metrics_out[name] = entry

    estimates: list[dict[str, Any]] = []
    if comparison_valid and contract:
        plan = contract.get("analysis_plan", {})
        estimators = {item["estimand_ref"]: item for item in plan.get("estimators", [])}
        rules = {item["estimand_ref"]: item for item in plan.get("decision_rules", [])}
        for estimand in plan.get("estimands", []):
            estimator = estimators.get(estimand["id"])
            rule = rules.get(estimand["id"])
            if not estimator or not rule:
                notes.append(f"estimand {estimand['id']} 缺 estimator 或 decision rule，這次不產生 estimate")
            elif estimator["type"] == "joint_cluster_bootstrap":
                # run envelope 只保存彙總後的 metrics，重抽 cluster 需要逐筆資料。
                # 缺輸入就不估計，也不靜默略過——沒有 estimate 的原因要留在紀錄裡。
                notes.append(
                    f"estimand {estimand['id']} 用 joint_cluster_bootstrap，"
                    "需要逐筆資料，compare-runs 讀不到，這次不產生 estimate"
                )
            else:
                estimates.append(estimate_from_plan(estimand, estimator, rule, baseline_run, treatment_run))

    result = {
        "experiment_id": experiment_id,
        "run_a": baseline_run["run_id"],
        "run_b": treatment_run["run_id"],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "comparability": {
            "dimensions": dimensions,
            "declared_variable": declared_variable,
        },
        "structurally_comparable": structurally_comparable,
        "controlled_variables_match": controlled_variables_match,
        "differences": differences,
        "comparison_valid": comparison_valid,
        "evidence_eligible": evidence["eligible"],
        "evidence_reasons": evidence["reasons"],
        "confounded": confounded,
        "confounded_reasons": confounded_reasons,
        "metrics": metrics_out,
        "estimates": estimates,
        "diagnostic_suggestions": [],
        "notes": notes,
    }

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("COMPARABILITY\n")
        for name, d in dimensions.items():
            print(f"{d['status']:8s} {name}")
        if declared_variable_name:
            tag = "CHANGED" if declared_variable["changed"] else "UNCHANGED"
            print(f"{tag:8s} {declared_variable_name}（宣告變因）")
        print()
        print(f"結構可比較：{'是' if structurally_comparable else '否'}")
        print(f"控制條件一致：{'是' if controlled_variables_match else '否'}")
        print(f"證據資格：{'合格' if evidence['eligible'] else '不合格'}")
        for reason in evidence["reasons"]:
            print(f"  - {reason}")
        if differences:
            print("\n具名差異")
            for d in differences:
                mark = "（宣告變因）" if d["declared"] else ""
                print(f"  [{d['severity']:13s}] {d['category']:9s} {d['key']}{mark}")
        print()
        if confounded:
            print("CONFOUNDED COMPARISON")
            for reason in confounded_reasons:
                print(f"  - {reason}")
            print("\n不得據此產生因果性結論。")
        elif not structurally_comparable:
            print("NOT STRUCTURALLY COMPARABLE")
            print("  - 沒有任何指標在兩邊都存在且定義一致")
            print("\n這不是 confounded，是沒有共同基準可比。同樣不得據此產生結論。")
        else:
            print("Comparable: YES")
            print(f"Changed variable: {declared_variable_name}")
        print()
        for name, m in metrics_out.items():
            if m["computed"]:
                print(f"{name}: baseline={m['baseline']} treatment={m['treatment']} Δ={m['absolute_diff']:+g} ({m['relative_diff']:+.1%})" if m["relative_diff"] is not None else f"{name}: baseline={m['baseline']} treatment={m['treatment']} Δ={m['absolute_diff']:+g}")
            else:
                print(f"{name}: 未計算（{'comparison invalid' if not comparison_valid else 'definition 不一致或資料缺失'}）")
        for note in notes:
            print(f"note: {note}")

    # confounded 與「沒有共同基準」是不同的失敗，但兩者都讓這次比較不可引用。
    return 1 if not comparison_valid or not evidence["eligible"] else 0
