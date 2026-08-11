"""測試共用工具：只走公開 CLI（`python -m experiment_records ...`），
不匯入套件內部函式。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "experiment_records", *args],
        capture_output=True,
        text=True,
    )


def write_record(project_root: Path, subdir: str, name: str, data: dict) -> Path:
    d = project_root / "records" / "experiments" / subdir
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def write_config(project_root: Path, relative: str, content: str = "k: v\n") -> Path:
    p = project_root / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def valid_definition(**overrides: object) -> dict:
    data = {
        "experiment_id": "demo-exp",
        "question": "top_k 提高是否讓 recall 提升？",
        "hypothesis": "提高 top_k 會提升 recall",
        "baseline": {
            "description": "baseline pipeline",
            "config_ref": "records/experiments/configs/baseline.yaml",
        },
        "treatment": {
            "description": "treatment pipeline",
            "config_ref": "records/experiments/configs/treatment.yaml",
            "variable": "top_k",
        },
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


def valid_run(**overrides: object) -> dict:
    data = {
        "run_id": "demo-run-1",
        "experiment_id": "demo-exp",
        "experiment_type": "rag",
        "created_at": "2026-01-01T00:00:00Z",
        "config_hash": "sha256:abc123",
        "config_ref": "records/experiments/configs/baseline.yaml",
        "schema_version": "1",
        "status": "completed",
    }
    data.update(overrides)
    return data


def valid_comparison(**overrides: object) -> dict:
    data = {
        "experiment_id": "demo-exp",
        "run_a": "demo-run-1",
        "run_b": "demo-run-2",
        "generated_at": "2026-01-01T00:00:00Z",
        "comparability": {"dimensions": {}, "declared_variable": {}, "other_differences": []},
        "comparison_valid": True,
        "confounded": False,
        "metrics": {},
    }
    data.update(overrides)
    return data


def valid_claim(**overrides: object) -> dict:
    data = {
        "claim_id": "demo-claim",
        "statement": "top_k 提升讓 recall 提高",
        "experiment_id": "demo-exp",
        "comparison_ref": "records/experiments/comparisons/demo-comparison.json",
        "metric": "recall_at_10",
        "expected_direction": "increase",
        "scope": "此資料集與此模型",
        "created_at": "2026-01-01T00:00:00Z",
    }
    data.update(overrides)
    return data
