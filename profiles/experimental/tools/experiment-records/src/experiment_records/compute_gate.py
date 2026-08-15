#!/usr/bin/env python3
"""判定一個 experiment 能不能升到 Contract 的 compute cascade 下一級。

用法：
  python3 compute_gate.py <gate-state.json> --contract <experiment-contract.json>
      --request-level L3
      [--comparison <comparison-result.json>] [--run <run.json> ...]
      [--run-ids a,b] [--decided-at 2026-01-01T00:00:00Z]

升級條件、中止條件與各級預算全部讀 Contract 的 `compute_cascade`，不從命令列帶
門檻。這是刻意的：門檻散在某次呼叫的參數裡，同一組紀錄就無法重跑出同一個判定。
翻譯只做一次，凍結在 Contract 裡。

這支工具仍然不解析 `scale_up_rule`／`abort_rule` 那兩句自然語言（ADR 0009 的邊界
不變）。把那兩句話翻成 `compute_cascade` 的 metric／comparator／threshold，是寫
Contract 的人的責任；翻完之後就是純機械比對。

判定順序，任一步失敗就停：
  1. 序列：不准跳級，也不准倒退申請已經通過的等級。
  2. abort：觸發就整條路線終止，不是補證據重來。
  3. budget：這一級的 run 實際用量不得超過該級預算。
  4. promotion：升級指標必須滿足門檻。

決定只由 gate-state、Contract 與傳入的紀錄決定。同一組輸入重跑會得到同一個
status、reason 與 checks；只有 decided_at 會變，可用 --decided-at 固定。

exit code：0 = 通過；1 = 沒過（failed 或 aborted）；2 = 用法錯誤（跳級、缺 Contract、
cascade 沒有這一級）。
"""

from __future__ import annotations

import argparse
import datetime
import json
import operator
from pathlib import Path
from typing import Any

from experiment_records.atomic_json import write_json

LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5"]
COMPARATORS = {
    ">": operator.gt, "<": operator.lt,
    ">=": operator.ge, "<=": operator.le,
    "==": operator.eq, "!=": operator.ne,
}
BUDGET_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("max_wall_clock_seconds", "duration_seconds", "牆鐘秒數"),
    ("max_samples", "resource_usage.samples", "樣本數"),
    ("max_cost_usd", "resource_usage.cost_usd", "花費"),
)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_threshold(value: float, comparator: str, threshold: float) -> bool:
    if comparator not in COMPARATORS:
        raise ValueError(f"不合法的 comparator：{comparator!r}，只接受 {sorted(COMPARATORS)}")
    return COMPARATORS[comparator](value, threshold)


def dotted(record: dict, path: str) -> Any:
    cursor: Any = record
    for part in path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def read_metric(rule: dict, comparison: dict | None, runs: list[dict]) -> tuple[Any, str | None]:
    """依 rule 的 source／metric／field 取值。取不到就回 (None, 原因)，不猜。"""
    metric, field, source = rule["metric"], rule["field"], rule["source"]

    if source == "comparison":
        if comparison is None:
            return None, "這條規則要讀 comparison，但沒有提供 --comparison"
        if not comparison.get("comparison_valid"):
            return None, "引用的 comparison 不可引用（confounded 或沒有共同基準），不能拿來當升級依據"
        entry = comparison.get("metrics", {}).get(metric)
        if not entry or not entry.get("computed"):
            return None, f"comparison 裡沒有算出 metric {metric!r}"
        if field not in entry:
            return None, f"comparison 的 metric {metric!r} 沒有欄位 {field!r}"
        return entry[field], None

    if not runs:
        return None, "這條規則要讀 run，但沒有提供 --run"
    values = [run.get("metrics", {}).get(metric) for run in runs]
    present = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not present:
        return None, f"提供的 run 都沒有 metric {metric!r}"
    # 多個 run 時取最差的一邊由 comparator 決定：中止條件看最嚴重，升級條件看最保守。
    return present, None


def evaluate_rule(rule: dict, comparison: dict | None, runs: list[dict], every: bool) -> tuple[bool | None, str]:
    """回傳 (是否成立, 說明)。取不到值時第一項是 None——「不知道」不等於「通過」。"""
    value, problem = read_metric(rule, comparison, runs)
    if problem is not None:
        return None, problem
    label = f"{rule['source']}.{rule['metric']}.{rule['field']}"
    if isinstance(value, list):
        outcomes = [check_threshold(v, rule["comparator"], rule["threshold"]) for v in value]
        met = all(outcomes) if every else any(outcomes)
        return met, f"{label} = {value}，門檻 {rule['comparator']} {rule['threshold']}"
    met = check_threshold(value, rule["comparator"], rule["threshold"])
    return met, f"{label} = {value}，門檻 {rule['comparator']} {rule['threshold']}"


def check_budget(budget: dict, runs: list[dict]) -> list[tuple[bool, str]]:
    checks: list[tuple[bool, str]] = []
    for limit_field, usage_field, noun in BUDGET_FIELDS:
        limit = budget.get(limit_field)
        if limit is None:
            continue
        for run in runs:
            usage = dotted(run, usage_field)
            if not isinstance(usage, (int, float)) or isinstance(usage, bool):
                continue
            run_id = run.get("run_id", "?")
            checks.append((
                usage <= limit,
                f"{run_id} 的{noun} {usage}，上限 {limit_field}={limit}",
            ))
    max_runs = budget.get("max_runs")
    if max_runs is not None:
        checks.append((len(runs) <= max_runs, f"提供 {len(runs)} 個 run，上限 max_runs={max_runs}"))
    return checks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gate_state")
    ap.add_argument("--contract", required=True, help="Experiment Contract，升級與中止條件的唯一來源")
    ap.add_argument("--request-level", required=True, choices=LEVELS)
    ap.add_argument("--comparison", help="promotion／abort 規則的 source 為 comparison 時需要")
    ap.add_argument("--run", action="append", default=[], help="可重複；預算檢查與 source 為 run 的規則會用到")
    ap.add_argument("--run-ids", default="", help="逗號分隔，記進這筆 history")
    ap.add_argument("--decided-at", help="RFC 3339 timestamp。省略時使用目前 UTC 時間")
    args = ap.parse_args(argv)

    gate_path = Path(args.gate_state).resolve()
    if gate_path.is_file():
        state = load_json(gate_path)
    else:
        state = {"experiment_id": gate_path.stem, "current_level": None, "history": [], "updated_at": now()}

    terminal_abort = next(
        (entry for entry in state.get("history", [])
         if isinstance(entry, dict) and entry.get("status") == "aborted"),
        None,
    )
    if terminal_abort is not None:
        print(f"ERROR 這條實驗路線已中止：{terminal_abort.get('reason', '未記錄原因')}")
        return 2

    contract = load_json(Path(args.contract).resolve())
    cascade = {entry["level"]: entry for entry in contract.get("compute_cascade", [])}
    requested = args.request_level

    if not cascade:
        print("ERROR Contract 沒有 compute_cascade；升級條件必須凍結在 Contract 裡，不從命令列帶")
        return 2
    if requested not in cascade:
        print(f"ERROR Contract 的 compute_cascade 沒有 {requested} 這一級，可用的是 {sorted(cascade)}")
        return 2

    rung = cascade[requested]
    comparison = load_json(Path(args.comparison).resolve()) if args.comparison else None
    runs = [load_json(Path(p).resolve()) for p in args.run]

    current = state.get("current_level")
    ladder = [level for level in LEVELS if level in cascade]
    expected_next = ladder[0] if current is None else (
        ladder[ladder.index(current) + 1] if current in ladder and ladder.index(current) + 1 < len(ladder) else None
    )

    checks: list[dict[str, Any]] = []
    reasons: list[str] = []
    status = "passed"

    # 1. 序列
    if requested != expected_next:
        print(f"ERROR 不能跳級：目前在 {current!r}，下一個只能申請 {expected_next!r}，收到 {requested!r}")
        return 2
    checks.append({"kind": "sequence", "passed": True, "detail": f"{current} -> {requested} 是相鄰的一級"})

    # 2. abort：觸發就終止，優先於其他檢查
    abort = rung.get("abort")
    if status == "passed" and abort:
        triggered, detail = evaluate_rule(abort, comparison, runs, every=False)
        if triggered is None:
            status = "failed"
            checks.append({"kind": "abort", "passed": False, "detail": detail})
            reasons.append(f"無法檢查中止條件：{detail}")
        elif triggered:
            status = "aborted"
            checks.append({"kind": "abort", "passed": False, "detail": detail})
            reasons.append(f"{abort['reason']}（{detail}）")
        else:
            checks.append({"kind": "abort", "passed": True, "detail": f"未觸發：{detail}"})

    # 3. budget
    if status == "passed":
        for passed, detail in check_budget(rung.get("budget") or {}, runs):
            checks.append({"kind": "budget", "passed": passed, "detail": detail})
            if not passed:
                status = "failed"
                reasons.append(f"超出 {requested} 的預算：{detail}")

    # 4. promotion
    promotion = rung.get("promotion")
    if status == "passed" and promotion:
        met, detail = evaluate_rule(promotion, comparison, runs, every=True)
        if met is None:
            status = "failed"
            checks.append({"kind": "promotion", "passed": False, "detail": detail})
            reasons.append(f"無法檢查升級條件：{detail}")
        elif not met:
            status = "failed"
            checks.append({"kind": "promotion", "passed": False, "detail": detail})
            reasons.append(f"升級條件沒過：{detail}")
        else:
            checks.append({"kind": "promotion", "passed": True, "detail": detail})

    if status == "passed" and not reasons:
        checked = "、".join(sorted({check["kind"] for check in checks}))
        reasons.append(f"{rung['stage']} 階段的 {checked} 檢查全部通過，升到 {requested}")

    decided_at = args.decided_at or now()
    entry = {
        "level": requested,
        "stage": rung["stage"],
        "status": status,
        "decided_at": decided_at,
        "reason": "；".join(reasons),
        "checks": checks,
        "run_ids": [r for r in args.run_ids.split(",") if r],
    }
    state["history"].append(entry)
    if status == "passed":
        state["current_level"] = requested
    state["updated_at"] = decided_at

    write_json(gate_path, state)

    print(f"{status.upper():8s} {requested}（{rung['stage']}）：{entry['reason']}")
    for check in checks:
        print(f"  [{'通過' if check['passed'] else '未過'}] {check['kind']:9s} {check['detail']}")
    if status == "passed":
        print(f"current_level 更新為 {requested}")
    elif status == "failed":
        print(f"current_level 維持 {current!r}，可以帶更足夠的證據重新申請 {requested}")
    else:
        print("aborted：這條實驗路線視為終止，不是重跑就能繼續的")

    return 0 if status == "passed" else 1
