"""組出獨立審核者收到的完整輸入。

包裡刻意沒有 producer 區塊。審核者不該知道這個主張是哪個 agent、用哪版 prompt 寫的：
知道了就會被它帶著走，而獨立性正是這裡要保住的東西。

同理，evidence_excerpts 把 locator 指到的值實際取出來，讓審核者不必相信主張對數字的
轉述。取不到就標 resolved=false，不用主張自己講的數字補上去。
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from experiment_records.project_layout import ProjectLayout
from experiment_records.ref_resolver import RefError, resolve_ref

DEFAULT_POLICY = {"required_reviewer_kind": "any_independent", "min_reviewers": 1}

# 明說看不到什麼，比讓審核者自己猜好。
OMITTED = [
    "claim.producer：寫這個主張的 agent、model 與 prompt 版本",
    "audit.producer：先前任何稽核者的身分",
    "專案裡未被 evidence_refs 或 comparison 引用到的其他紀錄",
]


class ReviewPackageError(Exception):
    """claim 不存在、Contract 找不到，或引用的比較結果載不進來。"""


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_claim(layout: ProjectLayout, claim_id: str) -> tuple[Path, dict[str, Any]]:
    for path in sorted((layout.records_root / "claims").glob("*.json")):
        try:
            claim = _load(path)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(claim, dict) and claim.get("claim_id") == claim_id:
            return path, claim
    raise ReviewPackageError(f"找不到 claim_id={claim_id!r}")


def _by_locator(document: Any, locator: str | None) -> tuple[bool, Any, str | None]:
    """依 dot-path 取值。取不到就回 (False, None, 原因)，不猜。"""
    if not locator:
        return True, None, None
    cursor = document
    for part in locator.split("."):
        if isinstance(cursor, dict) and part in cursor:
            cursor = cursor[part]
        elif isinstance(cursor, list) and part.isdigit() and int(part) < len(cursor):
            cursor = cursor[int(part)]
        else:
            return False, None, f"locator {locator!r} 在這份檔案裡取不到值"
    return True, cursor, None


def _excerpt(layout: ProjectLayout, entry: dict[str, Any]) -> dict[str, Any]:
    excerpt: dict[str, Any] = {"kind": entry.get("kind", "artifact"), "ref": entry.get("ref", "")}
    locator = entry.get("locator")
    if locator:
        excerpt["locator"] = locator
    try:
        path = resolve_ref(layout.project_root, entry.get("ref", ""))
    except RefError as error:
        return {**excerpt, "resolved": False, "problem": str(error)}

    try:
        document = _load(path)
    except (json.JSONDecodeError, OSError) as error:
        return {**excerpt, "resolved": False, "problem": f"載入失敗：{error}"}

    ok, value, problem = _by_locator(document, locator)
    if not ok:
        return {**excerpt, "resolved": False, "problem": problem or "取不到值"}
    return {**excerpt, "resolved": True, "value": value}


def _run_summaries(layout: ProjectLayout, experiment_id: str) -> list[dict[str, Any]]:
    """這個 experiment 的全部 run 摘要，含失敗與作廢的。

    只放成功的 run 會讓審核者看到一個比實際乾淨的世界，複現次數也會被高估。
    """
    summaries: list[dict[str, Any]] = []
    for path in sorted((layout.records_root / "runs").glob("*.json")):
        try:
            run = _load(path)
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(run, dict) or run.get("experiment_id") != experiment_id:
            continue
        summary: dict[str, Any] = {
            "run_id": run.get("run_id", path.stem),
            "status": run.get("status", "unknown"),
            "metrics": run.get("metrics", {}),
        }
        for source, target in (("stage", "stage"), ("seed", "seed"), ("invalid_reason", "invalid_reason")):
            if source in run:
                summary[target] = run[source]
        failure = run.get("failure")
        if isinstance(failure, dict) and "class" in failure:
            summary["failure_class"] = failure["class"]
        summaries.append(summary)
    return summaries


def build_review_package(layout: ProjectLayout, claim_id: str) -> dict[str, Any]:
    _, claim = _find_claim(layout, claim_id)
    experiment_id = claim.get("experiment_id", "")

    contract_path = layout.records_root / "definitions" / f"{experiment_id}.json"
    if not contract_path.is_file():
        raise ReviewPackageError(f"找不到 experiment {experiment_id!r} 的 Contract")
    contract = _load(contract_path)

    comparison_ref = claim.get("comparison_ref", "")
    try:
        comparison = _load(resolve_ref(layout.project_root, comparison_ref))
    except (RefError, json.JSONDecodeError, OSError) as error:
        raise ReviewPackageError(f"引用的 comparison 載不進來：{error}") from None

    derivation = contract.get("derivation", {})
    question = {
        "question": contract.get("question", ""),
        "hypothesis": contract.get("hypothesis", ""),
        "primary_metric": contract.get("primary_metric", ""),
        "secondary_metrics": contract.get("secondary_metrics", []),
    }
    for key in ("decision_rule", "contract_hash"):
        if key in contract:
            question[key] = contract[key]
    for key in ("falsifier", "tension"):
        if key in derivation:
            question[key] = derivation[key]

    claim_view = {
        key: claim[key]
        for key in ("statement", "scope", "claim_type", "metric", "expected_direction",
                    "stated_magnitude", "magnitude_type", "status")
        if key in claim
    }

    audit_path = layout.records_root / "audits" / f"{claim_id}.json"
    mechanical: dict[str, Any] = {}
    if audit_path.is_file():
        audit = _load(audit_path)
        if isinstance(audit, dict) and isinstance(audit.get("mechanical"), dict):
            mechanical = audit["mechanical"]

    return {
        "claim_id": claim_id,
        "experiment_id": experiment_id,
        "assembled_at": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy": contract.get("review_policy", dict(DEFAULT_POLICY)),
        "question": question,
        "claim": claim_view,
        "comparison": {
            "ref": comparison_ref,
            "comparison_valid": bool(comparison.get("comparison_valid")),
            "confounded": bool(comparison.get("confounded")),
            "structurally_comparable": bool(comparison.get("structurally_comparable")),
            "controlled_variables_match": bool(comparison.get("controlled_variables_match")),
            "confounded_reasons": comparison.get("confounded_reasons", []),
            "differences": comparison.get("differences", []),
            "metrics": comparison.get("metrics", {}),
            "notes": comparison.get("notes", []),
        },
        "evidence_excerpts": [_excerpt(layout, entry) for entry in claim.get("evidence_refs", [])],
        "mechanical": mechanical,
        "runs": _run_summaries(layout, experiment_id),
        "omitted": list(OMITTED),
    }
