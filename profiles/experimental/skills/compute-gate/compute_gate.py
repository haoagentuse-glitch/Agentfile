#!/usr/bin/env python3
"""判定一個 experiment 能不能從目前的 Compute Gate 等級升到下一級。

用法：
  python3 compute_gate.py <gate-state.json> --request-level L1 [--reason TEXT]

  # abort_rule 檢查（任何等級都可以帶，觸發就整條路線標 aborted）
    --abort-metric NAME --abort-comparator ">|<|>=|<=|==|!=" --abort-threshold N --abort-run <run.json>

  # scale_up_rule 檢查（L1 以後的升級通常要帶，沒帶就只做序列跟 budget 檢查）
    --scaleup-metric NAME --scaleup-comparator "..." --scaleup-threshold N
    [--scaleup-field absolute_diff|relative_diff]（預設 absolute_diff）
    --comparison <comparison-result.json>

  # pilot 預算檢查（只在 --request-level L3 時套用，讀 Contract 的 compute_budget）
    --contract <experiment-contract.json> --pilot-run <run.json>

  --output PATH 寫回更新後的 gate-state；不給就印出來，不落地。

gate-state.json 不存在時視為全新 experiment，current_level 當 null，第一次
只能申請 L0。等級一定要照 L0→L1→L2→L3→L4→L5 順序，不准跳，也不准倒退申請
已經 passed 的等級（要重跑同一級，直接開新 run，不必重新「申請」）。

Contract 裡的 scale_up_rule／abort_rule 是給人讀的自然語言，這支 script 不
自動解析——呼叫的人／agent 要自己把那句話翻成 --abort-metric 這些參數。這是
刻意的邊界：規則好不好、翻得對不對是語意判斷，一旦翻成明確的 metric／
comparator／threshold，比對數字就是純機械檢查，兩段不要混在一起。

exit code：0 = 通過，允許升級；1 = 沒過（failed 或 aborted）；2 = 用法錯誤
（例如跳級、gate-state 檔案本身壞掉）。
"""

from __future__ import annotations

import argparse
import datetime
import json
import operator
from pathlib import Path
from typing import Any

LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5"]
COMPARATORS = {
    ">": operator.gt, "<": operator.lt,
    ">=": operator.ge, "<=": operator.le,
    "==": operator.eq, "!=": operator.ne,
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_threshold(value: float, comparator: str, threshold: float) -> bool:
    if comparator not in COMPARATORS:
        raise ValueError(f"不合法的 comparator：{comparator!r}，只接受 {sorted(COMPARATORS)}")
    return COMPARATORS[comparator](value, threshold)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gate_state")
    ap.add_argument("--request-level", required=True, choices=LEVELS)
    ap.add_argument("--reason", default="")
    ap.add_argument("--run-ids", default="", help="逗號分隔，記進這筆 history")

    ap.add_argument("--abort-metric")
    ap.add_argument("--abort-comparator")
    ap.add_argument("--abort-threshold", type=float)
    ap.add_argument("--abort-run")

    ap.add_argument("--scaleup-metric")
    ap.add_argument("--scaleup-comparator")
    ap.add_argument("--scaleup-threshold", type=float)
    ap.add_argument("--scaleup-field", default="absolute_diff", choices=["absolute_diff", "relative_diff"])
    ap.add_argument("--comparison")

    ap.add_argument("--contract")
    ap.add_argument("--pilot-run")

    ap.add_argument("--output")
    args = ap.parse_args()

    gate_path = Path(args.gate_state).resolve()
    if gate_path.is_file():
        state = load_json(gate_path)
    else:
        state = {"experiment_id": gate_path.stem, "current_level": None, "history": [], "updated_at": now()}

    current = state.get("current_level")
    expected_next = LEVELS[0] if current is None else (
        LEVELS[LEVELS.index(current) + 1] if LEVELS.index(current) + 1 < len(LEVELS) else None
    )
    requested = args.request_level

    reasons: list[str] = []
    status = "passed"

    if requested != expected_next:
        print(f"ERROR 不能跳級：目前在 {current!r}，下一個只能申請 {expected_next!r}，收到 {requested!r}")
        return 2

    # abort_rule：任何等級都可能觸發，一旦觸發直接 aborted，不看其他檢查
    if args.abort_metric:
        run = load_json(Path(args.abort_run).resolve())
        value = run.get("metrics", {}).get(args.abort_metric)
        if value is None:
            print(f"ERROR run 裡沒有 metric {args.abort_metric!r}，無法檢查 abort_rule")
            return 2
        triggered = check_threshold(value, args.abort_comparator, args.abort_threshold)
        if triggered:
            status = "aborted"
            reasons.append(
                f"abort_rule 觸發：{args.abort_metric} = {value} {args.abort_comparator} {args.abort_threshold}"
            )

    # pilot 預算：只在申請 L3（小規模試跑）且提供 Contract／pilot-run 時檢查
    if status == "passed" and requested == "L3" and args.contract and args.pilot_run:
        contract = load_json(Path(args.contract).resolve())
        pilot_run = load_json(Path(args.pilot_run).resolve())
        budget = contract.get("compute_budget", {})
        max_minutes = budget.get("pilot_max_minutes")
        duration_min = (pilot_run.get("duration_seconds") or 0) / 60
        if max_minutes is not None and duration_min > max_minutes:
            status = "failed"
            reasons.append(f"pilot 耗時 {duration_min:.1f} 分鐘超過 compute_budget.pilot_max_minutes={max_minutes}")

    # scale_up_rule：檢查 pilot/前一級的證據是否足以支持升級
    if status == "passed" and args.scaleup_metric:
        comparison = load_json(Path(args.comparison).resolve())
        if not comparison.get("comparison_valid"):
            status = "failed"
            reasons.append("scale_up_rule 檢查用的 comparison 本身是 confounded／invalid，不能拿來當升級依據")
        else:
            metric_entry = comparison.get("metrics", {}).get(args.scaleup_metric)
            if not metric_entry or not metric_entry.get("computed"):
                status = "failed"
                reasons.append(f"comparison 裡沒有算出 metric {args.scaleup_metric!r}")
            else:
                value = metric_entry[args.scaleup_field]
                met = check_threshold(value, args.scaleup_comparator, args.scaleup_threshold)
                if not met:
                    status = "failed"
                    reasons.append(
                        f"scale_up_rule 沒過：{args.scaleup_metric}.{args.scaleup_field} = {value}，"
                        f"未滿足 {args.scaleup_comparator} {args.scaleup_threshold}"
                    )

    if status == "passed" and not reasons:
        reasons.append(args.reason or f"通過序列與已提供的檢查，升到 {requested}")

    entry = {
        "level": requested,
        "status": status,
        "decided_at": now(),
        "reason": "；".join(reasons),
        "run_ids": [r for r in args.run_ids.split(",") if r],
    }
    state["history"].append(entry)
    if status == "passed":
        state["current_level"] = requested
    state["updated_at"] = now()

    if args.output:
        Path(args.output).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{status.upper():8s} {requested}：{entry['reason']}")
    if status == "passed":
        print(f"current_level 更新為 {requested}")
    else:
        print(f"current_level 維持 {current!r}，可以帶更足夠的證據重新申請 {requested}" if status == "failed"
              else "aborted：這條實驗路線視為終止，不是重跑就能繼續的")

    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
