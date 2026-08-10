#!/usr/bin/env python3
"""Deterministic checks for an Experiment Contract. No LLM judgment involved.

用法：
  python3 experiment_lint.py <contract.json>

只用標準函式庫，不裝額外依賴。檢查兩類事：
1. 對照 experiment-contract.schema.json 遞迴檢查必填欄位是否齊全、enum 是否合法。
2. 讀 baseline/treatment 的 config_ref，比對 controlled_variables 宣告的欄位
   是否真的相同、有沒有未宣告的差異——這是機械判定，不是 agent 讀過去覺得像。

PASS/WARN 不擋執行；ERROR 用 exit code 1 擋（"Run blocked"）。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

def find_schema_dir(start: Path) -> Path:
    """從 script 位置往上找 records/experiments/schemas/。這支 script 在來源包裡是
    profiles/experimental/skills/experiment-lint/，投影到目標專案後變成
    .agents/skills/experiment-lint/——兩邊到 repo 根目錄的深度不同，用固定層數會
    在其中一邊找錯，所以往上搜尋而非寫死層數。"""
    for candidate in [start, *start.parents]:
        probe = candidate / "records" / "experiments" / "schemas"
        if probe.is_dir():
            return probe
    raise FileNotFoundError("找不到 records/experiments/schemas/——確認在專案內執行")


SCHEMA_DIR = find_schema_dir(Path(__file__).resolve().parent)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def check_schema(instance: dict, schema: dict, path: str, results: list[tuple[str, str]]) -> None:
    """遞迴檢查 required 欄位與 enum 限制。results 收集 (level, message)。"""
    required = schema.get("required", [])
    properties = schema.get("properties", {})

    for key in required:
        label = f"{path}.{key}" if path else key
        if key not in instance or instance[key] in (None, "", []):
            results.append(("ERROR", f"missing required field: {label}"))
        else:
            results.append(("PASS", f"{label} defined"))

    for key, subschema in properties.items():
        if key not in instance:
            continue
        value = instance[key]
        label = f"{path}.{key}" if path else key

        enum = subschema.get("enum")
        if enum is not None and value not in enum:
            results.append(("ERROR", f"{label} = {value!r} not in allowed values {enum}"))

        if subschema.get("type") == "object" and isinstance(value, dict):
            check_schema(value, subschema, label, results)


def diff_configs(contract: dict, results: list[tuple[str, str]]) -> None:
    """比對 baseline/treatment config，檢查 controlled_variables 是否真的一致，
    以及有沒有未宣告的差異（confound）。config_ref 路徑找不到時只 WARN，不擋——
    這階段不強制要求檔案已存在（Contract 可能先 draft，config 還沒寫完）。"""
    baseline = contract.get("baseline", {})
    treatment = contract.get("treatment", {})
    controlled = set(contract.get("controlled_variables", []))
    treatment_var = treatment.get("variable")

    contract_path = Path(contract.get("_contract_path", "."))
    base_ref = baseline.get("config_ref")
    treat_ref = treatment.get("config_ref")
    if not base_ref or not treat_ref:
        return

    base_path = (contract_path.parent / base_ref).resolve()
    treat_path = (contract_path.parent / treat_ref).resolve()
    if not base_path.is_file() or not treat_path.is_file():
        results.append(("WARN", "baseline/treatment config_ref 尚未存在，跳過 confound 檢查（Contract 還在 draft 階段時正常）"))
        return

    try:
        base_cfg = load_json(base_path)
        treat_cfg = load_json(treat_path)
    except json.JSONDecodeError as e:
        results.append(("ERROR", f"config 不是合法 JSON：{e}"))
        return

    all_keys = set(base_cfg) | set(treat_cfg)
    undeclared = []
    for key in sorted(all_keys):
        bv, tv = base_cfg.get(key, "<absent>"), treat_cfg.get(key, "<absent>")
        if bv == tv:
            continue
        if key in controlled:
            results.append((
                "ERROR",
                f"declared controlled_variable '{key}' actually differs: "
                f"baseline={bv!r} treatment={tv!r}. Experiment is not identifiable. Run blocked.",
            ))
        elif key != treatment_var:
            undeclared.append((key, bv, tv))

    for key, bv, tv in undeclared:
        results.append((
            "WARN",
            f"undeclared difference in '{key}': baseline={bv!r} treatment={tv!r} — "
            f"is this the treatment variable or a controlled variable? declare it in the Contract",
        ))

    if "seed" not in controlled and "seed" not in (treatment_var or ""):
        results.append(("WARN", "random seed unspecified in controlled_variables"))


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: python3 experiment_lint.py <contract.json>", file=sys.stderr)
        return 2

    contract_path = Path(sys.argv[1]).resolve()
    contract = load_json(contract_path)
    contract["_contract_path"] = str(contract_path)

    schema_path = SCHEMA_DIR / "experiment-contract.schema.json"
    schema = load_json(schema_path)

    results: list[tuple[str, str]] = []
    check_schema({k: v for k, v in contract.items() if k != "_contract_path"}, schema, "", results)
    diff_configs(contract, results)

    for level, msg in results:
        print(f"{level:5s} {msg}")

    errors = [m for lvl, m in results if lvl == "ERROR"]
    print()
    if errors:
        print(f"{len(errors)} error(s). Run blocked.")
        return 1
    print("Contract identifiable. OK to lock / run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
