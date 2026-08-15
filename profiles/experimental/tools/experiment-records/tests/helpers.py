"""測試共用工具：只走公開 CLI，不匯入套件內部函式。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "experiment_records", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_record(project_root: Path, subdir: str, name: str, data: dict) -> Path:
    root = project_root / "records" / "experiments"
    if subdir == "lifecycles" and "history" in data:
        _ensure_lifecycle_evidence(root, data["history"])
        last_path: Path | None = None
        for sequence, transition in enumerate(data["history"], start=1):
            event = {
                "event_id": f"{name}-{sequence:04d}",
                "experiment_id": data["experiment_id"],
                "sequence": sequence,
                **transition,
            }
            last_path = _write_json(root / subdir / f"{name}-{sequence:04d}.json", event)
        assert last_path is not None
        return last_path
    return _write_json(root / subdir / f"{name}.json", data)


def _ensure_lifecycle_evidence(root: Path, history: list[dict]) -> None:
    if any(event["to_state"] == "awaiting_claim" for event in history):
        comparison = root / "comparisons" / "demo-comparison.json"
        if not comparison.exists():
            _write_json(comparison, valid_comparison())
        for event in history:
            if event["to_state"] == "awaiting_claim" and not event["evidence_refs"]:
                event["evidence_refs"] = ["records/experiments/comparisons/demo-comparison.json"]
    if any(event["to_state"] == "awaiting_review" for event in history):
        claim = root / "claims" / "demo-claim.json"
        if not claim.exists():
            _write_json(claim, valid_claim())
        audit = root / "audits" / "demo-audit.json"
        if not audit.exists():
            _write_json(audit, valid_audit())
        for event in history:
            if event["to_state"] == "awaiting_review" and not event["evidence_refs"]:
                event["evidence_refs"] = ["records/experiments/audits/demo-audit.json"]


def write_config(project_root: Path, relative: str, content: str = "k: v\n") -> Path:
    path = project_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def valid_definition(**overrides: object) -> dict:
    data = {
        "experiment_id": "demo-exp",
        "question": "top_k 提高是否讓 recall 提升？",
        "hypothesis": "提高 top_k 會提升 recall",
        "baseline": {"description": "baseline pipeline", "config_ref": "records/experiments/configs/baseline.yaml"},
        "treatment": {"description": "treatment pipeline", "config_ref": "records/experiments/configs/treatment.yaml", "variable": "top_k"},
        "controlled_variables": ["dataset"],
        "primary_metric": "recall_at_10",
        "decision_rule": "recall 提升至少 0.05 視為成功",
        "compute_budget": {"pilot_max_minutes": 5, "pilot_max_samples": 100},
        "abort_rule": "guardrail 超標立即中止",
        "status": "draft",
        "created_at": "2026-01-01T00:00:00Z",
    }
    data.update(overrides)
    return data


def valid_derivation(**overrides: object) -> dict:
    data = {
        "primitives": [{"id": "retrieval_coverage", "definition": "答案所需片段被取回的比例"}],
        "assumptions": [{"id": "a1", "statement": "評估集沒有洩漏到索引裡", "status": "unverified"}],
        "mechanism_model": {
            "summary": "提高 top_k 增加覆蓋率，但引入干擾片段並吃掉 context 額度",
            "variables": ["top_k", "coverage", "distractor_rate"],
        },
        "tension": "覆蓋率與干擾雜訊的取捨",
        "falsifier": "預先指定的 slice 中 recall 沒有提升",
        "minimal_decisive_test": "固定語料與查詢，只掃 top_k，重複三個 seed",
        "expected_observations": ["recall 隨 top_k 遞增後趨於平緩"],
        "failure_update": [{"when": "recall 沒提升", "update_assumption_id": "a1", "to": "refuted"}],
        "source_refs": [],
        "counterexamples": [],
        "novelty_status": "unverified",
    }
    data.update(overrides)
    return data


def valid_run(**overrides: object) -> dict:
    data = {
        "run_id": "demo-run-1", "experiment_id": "demo-exp", "experiment_type": "rag",
        "created_at": "2026-01-01T00:00:00Z", "config_hash": "sha256:abc123",
        "config_ref": "records/experiments/configs/baseline.yaml", "schema_version": "1",
        "status": "completed",
    }
    data.update(overrides)
    return data


def valid_comparison(**overrides: object) -> dict:
    data = {
        "experiment_id": "demo-exp", "run_a": "demo-run-1", "run_b": "demo-run-2",
        "generated_at": "2026-01-01T00:00:00Z",
        "comparability": {"dimensions": {}, "declared_variable": {}},
        "structurally_comparable": True, "controlled_variables_match": True, "differences": [],
        "comparison_valid": True, "confounded": False, "metrics": {},
    }
    data.update(overrides)
    return data


def valid_claim(**overrides: object) -> dict:
    data = {
        "claim_id": "demo-claim", "statement": "top_k 提升讓 recall 提高",
        "experiment_id": "demo-exp", "comparison_ref": "records/experiments/comparisons/demo-comparison.json",
        "metric": "recall_at_10", "expected_direction": "increase", "scope": "此資料集與此模型",
        "created_at": "2026-01-01T00:00:00Z",
    }
    data.update(overrides)
    return data


def valid_audit(**overrides: object) -> dict:
    data = {
        "claim_id": "demo-claim", "audited_at": "2026-01-01T00:00:00Z",
        "mechanical": {
            "reference_exists": True, "comparison_valid": True, "metric_exists": True,
            "direction_matches": True, "magnitude_matches": None, "mechanical_pass": True,
        },
        "scope_verdict": "fully_supported", "scope_reasoning": "證據範圍一致",
        "final_verdict": "fully_supported",
    }
    data.update(overrides)
    return data


def valid_lifecycle(*states: str, **overrides: object) -> dict:
    previous: str | None = None
    history = []
    for index, state in enumerate(states):
        history.append({
            "from_state": previous,
            "to_state": state,
            "occurred_at": f"2026-01-01T00:{index:02d}:00Z",
            "reason": f"進入 {state}",
            "evidence_refs": [],
        })
        previous = state
    data = {"experiment_id": "demo-exp", "history": history}
    data.update(overrides)
    return data
