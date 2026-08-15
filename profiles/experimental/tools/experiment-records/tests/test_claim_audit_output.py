"""claim_audit.py 的實際輸出必須通過 claim-audit-result schema。

跟 test_compare_runs_output.py 同一個目的：生產者與驗證器之間的端到端契約測試。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from helpers import run_cli, valid_claim, valid_comparison, write_record


def _metric(**overrides: object) -> dict:
    entry = {
        "definition_consistent": True, "computed": True,
        "baseline": 0.62, "treatment": 0.71,
        "absolute_diff": 0.09, "relative_diff": 0.145,
    }
    entry.update(overrides)
    return entry


@pytest.fixture
def scenario(project: Path):
    def build(comparison_overrides: dict, claim_overrides: dict) -> Path:
        overrides = {"metrics": {"recall_at_10": _metric()}, **comparison_overrides}
        comparison = valid_comparison(**overrides)
        write_record(project, "comparisons", "demo-comparison", comparison)
        write_record(project, "claims", "demo-claim", valid_claim(**claim_overrides))
        return project

    return build


def _audit(project: Path) -> tuple[subprocess.CompletedProcess[str], dict | None]:
    output = project / "records" / "experiments" / "audits" / "demo-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run_cli(
        "claim-audit",
        "records/experiments/claims/demo-claim.json",
        "--output",
        str(output),
        cwd=project,
    )
    written = json.loads(output.read_text(encoding="utf-8")) if output.is_file() else None
    return result, written


def test_pending_audit_output_validates(scenario) -> None:
    """機械段通過、語意段還沒判——這是合法的中間狀態，不得寫出 final_verdict。"""
    project = scenario({}, {})

    audit, written = _audit(project)

    assert written is not None, audit.stdout + audit.stderr
    assert written["mechanical"]["mechanical_pass"] is True
    assert written["scope_verdict"] == "pending"
    assert "final_verdict" not in written

    validate = run_cli("validate", str(project))
    assert validate.returncode == 0, validate.stdout + validate.stderr


def test_existing_reviewed_audit_is_not_overwritten(scenario) -> None:
    project = scenario({}, {})
    first, written = _audit(project)
    assert first.returncode == 0
    assert written is not None

    output = project / "records" / "experiments" / "audits" / "demo-audit.json"
    written.update({
        "scope_verdict": "fully_supported",
        "scope_reasoning": "證據與主張範圍一致",
        "final_verdict": "fully_supported",
    })
    output.write_text(json.dumps(written, ensure_ascii=False, indent=2), encoding="utf-8")
    reviewed = output.read_text(encoding="utf-8")

    second, _ = _audit(project)

    assert second.returncode == 2
    assert "已存在" in second.stdout
    assert output.read_text(encoding="utf-8") == reviewed

def test_confounded_comparison_produces_unsupported_verdict(scenario) -> None:
    project = scenario(
        {
            "comparison_valid": False, "confounded": True,
            "controlled_variables_match": False,
            "metrics": {"recall_at_10": _metric(computed=False)},
        },
        {},
    )

    audit, written = _audit(project)

    assert written is not None, audit.stdout + audit.stderr
    assert written["mechanical"]["comparison_valid"] is False
    assert written["mechanical"]["comparison_confounded"] is True
    assert written["final_verdict"] == "unsupported"
    assert any("confounded" in reason for reason in written["mechanical_reasons"])

    validate = run_cli("validate", str(project))
    assert validate.returncode == 0, validate.stdout + validate.stderr


def test_structurally_incomparable_is_reported_as_such_not_as_confounded(scenario) -> None:
    """不可引用有兩種原因；稽核紀錄必須說得出是哪一種。"""
    project = scenario(
        {
            "comparison_valid": False, "confounded": False,
            "structurally_comparable": False,
            "metrics": {"recall_at_10": _metric(computed=False)},
        },
        {},
    )

    _, written = _audit(project)

    assert written["mechanical"]["comparison_confounded"] is False
    assert any("沒有共同基準可比" in reason for reason in written["mechanical_reasons"])


def test_wrong_direction_is_caught_mechanically(scenario) -> None:
    project = scenario({}, {"expected_direction": "decrease"})

    audit, written = _audit(project)

    assert written["mechanical"]["direction_matches"] is False
    assert written["mechanical"]["mechanical_pass"] is False
    assert written["final_verdict"] == "unsupported"

    validate = run_cli("validate", str(project))
    assert validate.returncode == 0, validate.stdout + validate.stderr


def test_missing_comparison_is_unauditable(scenario) -> None:
    project = scenario({}, {"comparison_ref": "records/experiments/comparisons/demo-comparison.json"})
    (project / "records" / "experiments" / "comparisons" / "demo-comparison.json").unlink()

    _, written = _audit(project)

    assert written["mechanical"]["reference_exists"] is False
    assert written["final_verdict"] == "unauditable"
