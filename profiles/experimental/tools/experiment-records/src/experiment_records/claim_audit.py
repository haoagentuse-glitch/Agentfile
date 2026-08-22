#!/usr/bin/env python3
"""稽核一個 claim 是否真的追得回具體 run／comparison，數字對不對。

用法：
  python3 claim_audit.py <claim.json> [--output PATH] [--json]

只做機械可判定的部分：
  - comparison_ref 存不存在、載不載得進來
  - 引用的 comparison-result 是不是 comparison_valid（confounded 的一律擋）
  - claim 引用的 metric 有沒有被算出來
  - claim 宣稱的方向／幅度是否符合 comparison-result 的實際數字

「這個結論有沒有超出證據範圍」（例如把單一資料集的結果講成通用結論）是語意判斷，
這支 script 不做——mechanical_pass 為 true 時，scope_verdict 留 "pending"，
交給呼叫的 agent 依 claim-audit 技能的判準補上，這是刻意的分工，不是漏做。

exit code：0 = mechanical_pass（scope 還沒判，不代表 claim 整體成立），
           1 = mechanical 沒過（unauditable 或 unsupported，不用再看 scope）。
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
from typing import Any

from experiment_records.atomic_json import write_json
from experiment_records.evidence_policy import evaluate_evidence_policy


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_records_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        probe = candidate / "records" / "experiments"
        if (probe / "schemas").is_dir():
            return probe
    raise FileNotFoundError("找不到 records/experiments/——確認在專案內執行")


TOLERANCE = 0.10  # stated_magnitude 容許 10% 相對誤差


def load_audit_evidence(
    claim: dict[str, Any], comparison: dict[str, Any] | None, records_root: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """載入凍結 Contract 與 claim 所依賴的底層 runs。"""
    experiment_id = claim.get("experiment_id")
    contract_path = records_root / "definitions" / f"{experiment_id}.json"
    contract = load_json(contract_path) if contract_path.is_file() else {}

    requested_ids: set[str] = set()
    if comparison is not None:
        requested_ids.update(
            run_id
            for run_id in (comparison.get("run_a"), comparison.get("run_b"))
            if isinstance(run_id, str)
        )
    project_root = records_root.parent.parent
    direct_paths: list[Path] = []
    for evidence_ref in claim.get("evidence_refs", []):
        if evidence_ref.get("kind") != "run":
            continue
        ref = evidence_ref.get("ref")
        if isinstance(ref, str):
            path = (project_root / ref).resolve()
            if path.is_file() and project_root.resolve() in path.parents:
                direct_paths.append(path)

    runs_by_id: dict[str, dict[str, Any]] = {}
    for path in [*(records_root / "runs").glob("*.json"), *direct_paths]:
        run = load_json(path)
        run_id = run.get("run_id")
        if isinstance(run_id, str) and run.get("experiment_id") == experiment_id:
            runs_by_id[run_id] = run
    requested_ids.update(
        run_id
        for path in direct_paths
        if isinstance((run_id := load_json(path).get("run_id")), str)
    )
    return contract, [runs_by_id[run_id] for run_id in sorted(requested_ids) if run_id in runs_by_id]


def audit(claim_path: Path) -> dict[str, Any]:
    claim = load_json(claim_path)
    records_root = find_records_root(claim_path.parent)

    reasons: list[str] = []
    reference_exists = False
    comparison_valid: bool | None = None
    comparison_confounded: bool | None = None
    metric_exists: bool | None = None
    direction_matches: bool | None = None
    magnitude_matches: bool | None = None
    comparison: dict | None = None

    # comparison_ref 一律相對 project root 解析，跟 experiment_records 的 ref 規則一致。
    project_root = records_root.parent.parent
    comparison_ref = claim.get("comparison_ref")
    comparison_path = (project_root / comparison_ref).resolve() if comparison_ref else None
    if comparison_path and comparison_path.is_file():
        reference_exists = True
        comparison = load_json(comparison_path)
    else:
        reasons.append(f"comparison_ref 指到的檔案不存在：{comparison_ref!r}")

    if reference_exists and comparison is not None:
        if comparison.get("experiment_id") != claim.get("experiment_id"):
            reasons.append(
                f"claim.experiment_id={claim.get('experiment_id')!r} 跟引用的 comparison 的 "
                f"experiment_id={comparison.get('experiment_id')!r} 對不上"
            )
        comparison_valid = bool(comparison.get("comparison_valid"))
        comparison_confounded = bool(comparison.get("confounded"))
        if not comparison_valid:
            # 分開講：confounded 是條件沒守住，非 confounded 的 invalid 是沒有共同基準。
            cause = "confounded" if comparison_confounded else "沒有共同基準可比"
            reasons.append(f"引用的 comparison 不可引用（{cause}），不得用來支撐結論（規則 10）")

        metric_name = claim.get("metric")
        metric_entry = comparison.get("metrics", {}).get(metric_name)
        metric_exists = bool(metric_entry and metric_entry.get("computed"))
        if not metric_exists:
            reasons.append(f"metric '{metric_name}' 在引用的 comparison 裡沒有被算出來（可能是 comparison invalid 或 metric definition 不一致）")

        if comparison_valid and metric_exists:
            actual_diff = metric_entry["absolute_diff"]
            expected = claim.get("expected_direction")
            if expected == "increase":
                direction_matches = actual_diff > 0
            elif expected == "decrease":
                direction_matches = actual_diff < 0
            elif expected == "no_change":
                direction_matches = abs(actual_diff) < 1e-9
            else:
                direction_matches = False
                reasons.append(f"expected_direction={expected!r} 不是合法值")
            if direction_matches is False:
                reasons.append(
                    f"claim 宣稱 metric 應該 {expected}，但實際 absolute_diff={actual_diff!r}——方向對不上"
                )

            stated = claim.get("stated_magnitude")
            if stated is not None:
                mtype = claim.get("magnitude_type", "absolute")
                actual = metric_entry["absolute_diff"] if mtype == "absolute" else metric_entry["relative_diff"]
                if actual is None:
                    magnitude_matches = False
                    reasons.append(f"comparison 裡沒有 {mtype} 差異可比對")
                else:
                    tol = max(abs(actual) * TOLERANCE, 1e-9)
                    magnitude_matches = abs(actual - stated) <= tol
                    if not magnitude_matches:
                        reasons.append(
                            f"claim 宣稱的幅度 {stated!r}（{mtype}）跟實際 {actual!r} 差距超過容許誤差（±{TOLERANCE:.0%}）"
                        )

    contract, evidence_runs = load_audit_evidence(claim, comparison, records_root)
    evidence = evaluate_evidence_policy(contract, evidence_runs)
    if not evidence["eligible"]:
        reasons.extend(f"證據不合格：{reason}" for reason in evidence["reasons"])

    mechanical_pass = bool(
        reference_exists
        and comparison_valid
        and metric_exists
        and direction_matches
        and (magnitude_matches is not False)
        and evidence["eligible"]
    )

    if mechanical_pass:
        scope_verdict = "pending"
    elif not reference_exists:
        scope_verdict = "unauditable"
    elif comparison_valid is False:
        scope_verdict = "unsupported"
    elif metric_exists is False:
        scope_verdict = "unauditable"
    else:
        scope_verdict = "unsupported"

    result = {
        "claim_id": claim.get("claim_id"),
        "audited_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evidence_eligible": evidence["eligible"],
        "evidence_reasons": evidence["reasons"],
        "mechanical": {
            "reference_exists": reference_exists,
            "comparison_valid": comparison_valid,
            "comparison_confounded": comparison_confounded,
            "metric_exists": metric_exists,
            "direction_matches": direction_matches,
            "magnitude_matches": magnitude_matches,
            "mechanical_pass": mechanical_pass,
        },
        "mechanical_reasons": reasons,
        "scope_verdict": scope_verdict,
        "scope_reasoning": "",
    }
    # scope_verdict 還是 pending 時不寫 final_verdict——「還沒判」不是一種結論。
    if scope_verdict != "pending":
        result["final_verdict"] = scope_verdict
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("claim")
    ap.add_argument("--output")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    result = audit(Path(args.claim).resolve())

    if args.output:
        try:
            write_json(Path(args.output), result, exclusive=True)
        except FileExistsError:
            print(f"ERROR 稽核輸出已存在，不覆蓋：{args.output}")
            return 2

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        m = result["mechanical"]
        print(f"claim_id: {result['claim_id']}")
        print(f"reference_exists   : {m['reference_exists']}")
        print(f"comparison_valid   : {m['comparison_valid']}")
        print(f"metric_exists      : {m['metric_exists']}")
        print(f"direction_matches  : {m['direction_matches']}")
        print(f"magnitude_matches  : {m['magnitude_matches']}")
        print(f"evidence_eligible  : {result['evidence_eligible']}")
        print()
        if result["mechanical_reasons"]:
            print("原因：")
            for r in result["mechanical_reasons"]:
                print(f"  - {r}")
            print()
        if result["scope_verdict"] == "pending":
            print("MECHANICAL PASS —— 數字跟方向都對得上，接下來換語意判斷：")
            print("這個結論有沒有超出證據涵蓋的範圍？參考 claim-audit 技能的判準，")
            print("把 scope_verdict 填成 fully_supported／partially_supported／overreaching 之一。")
        else:
            print(f"MECHANICAL FAIL —— final_verdict = {result['final_verdict']}，不需要再判斷 scope。")

    return 0 if result["scope_verdict"] == "pending" else 1
