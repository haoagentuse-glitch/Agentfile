from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def _schema(project: Path, name: str) -> dict:
    path = project / "records" / "experiments" / "schemas" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _errors(project: Path, name: str, instance: dict) -> list:
    return list(Draft202012Validator(_schema(project, name)).iter_errors(instance))


def _contract() -> dict:
    from helpers import valid_definition

    return valid_definition(evidence_policy={"eligible_run_stages": ["main", "replication"]})


def test_contract_requires_nonempty_declared_eligible_run_stages(project: Path) -> None:
    assert _errors(project, "experiment-contract.schema.json", _contract()) == []

    invalid = _contract()
    invalid["evidence_policy"]["eligible_run_stages"] = []
    assert _errors(project, "experiment-contract.schema.json", invalid)


def test_compute_rules_discriminate_run_and_comparison_fields(project: Path) -> None:
    base = _contract()
    base["compute_cascade"] = [{"stage": "pilot", "level": "L1"}]

    valid_rules = [
        {"metric": "m", "source": "run", "field": "value", "run_scope": "baseline", "comparator": ">=", "threshold": 1},
        {"metric": "m", "source": "comparison", "field": "relative_diff", "comparator": ">=", "threshold": 0.1},
    ]
    for rule in valid_rules:
        candidate = json.loads(json.dumps(base))
        candidate["compute_cascade"][0]["promotion"] = rule
        assert _errors(project, "experiment-contract.schema.json", candidate) == []

    invalid_rules = [
        {"metric": "m", "source": "run", "field": "baseline", "run_scope": "all", "comparator": ">=", "threshold": 1},
        {"metric": "m", "source": "run", "field": "value", "comparator": ">=", "threshold": 1},
        {"metric": "m", "source": "comparison", "field": "value", "comparator": ">=", "threshold": 1},
        {"metric": "m", "source": "comparison", "field": "baseline", "run_scope": "all", "comparator": ">=", "threshold": 1},
    ]
    for rule in invalid_rules:
        candidate = json.loads(json.dumps(base))
        candidate["compute_cascade"][0]["promotion"] = rule
        assert _errors(project, "experiment-contract.schema.json", candidate)


def test_comparison_and_audit_persist_evidence_decision(project: Path) -> None:
    from helpers import valid_audit, valid_comparison

    comparison = valid_comparison(evidence_eligible=False, evidence_reasons=["stage 不合格"])
    audit = valid_audit(evidence_eligible=False, evidence_reasons=["comparison evidence 不合格"])
    assert _errors(project, "comparison-result.schema.json", comparison) == []
    assert _errors(project, "claim-audit-result.schema.json", audit) == []


def test_gate_history_persists_evidence_decision(project: Path) -> None:
    state = {
        "experiment_id": "demo-exp",
        "current_level": None,
        "history": [{
            "level": "L1", "stage": "pilot", "status": "failed",
            "decided_at": "2026-01-01T00:00:00Z", "reason": "證據不合格",
            "evidence_eligible": False, "evidence_reasons": ["run stage 不合格"],
        }],
        "updated_at": "2026-01-01T00:00:00Z",
    }
    assert _errors(project, "gate-state.schema.json", state) == []
