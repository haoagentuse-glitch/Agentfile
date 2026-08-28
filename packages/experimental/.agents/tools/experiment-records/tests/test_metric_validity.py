"""指標效度與 lock 前的可行性檢查（ADR 0021）。

兩組不變量：
一、判定門檻只能掛在「說得出用途、指得出證據」的指標上。
二、可行性檢查要留下可重跑的命令與證據位置；validator 不從散文猜數字。
"""

from __future__ import annotations

import json
from pathlib import Path

from experiment_records.project_layout import resolve_layout
from experiment_records.validation import validator_for
from helpers import run_cli, valid_definition, valid_metric, write_config, write_record

EVIDENCE_REF = "docs/evidence/metric-validity.md"


def _errors(project: Path, name: str, instance: dict) -> list:
    return list(validator_for(resolve_layout(project), name).iter_errors(instance))


def _eligible_validity(**overrides) -> dict:
    data = {
        "intended_use": "在固定評估集上比較檢索設定的召回差異",
        "evidence_refs": [EVIDENCE_REF],
        "limitations": ["標註者間一致性只在單一語料上量過"],
        "threshold_eligible": True,
    }
    data.update(overrides)
    return data


def _unvalidated_metric(name: str) -> dict:
    """還沒驗證過的指標。helpers 的預設是「可承載門檻」，這裡刻意拿掉。"""
    metric = valid_metric(name=name)
    metric.pop("validity")
    return metric


def _project_with_evidence(project: Path) -> None:
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")
    write_config(project, EVIDENCE_REF, "# 標籤稽核\n\n誤差率 1.2%。\n")


# --- 指標效度 ---------------------------------------------------------------


def test_threshold_eligible_requires_intended_use_and_evidence(project: Path) -> None:
    """宣稱可承載門檻，就必須說得出用途、指得出證據。"""
    assert _errors(project, "metric-definition.schema.json", valid_metric(validity=_eligible_validity())) == []

    for missing in ("intended_use", "evidence_refs"):
        broken = _eligible_validity()
        broken.pop(missing)
        assert _errors(project, "metric-definition.schema.json", valid_metric(validity=broken)), missing

    empty_evidence = _eligible_validity(evidence_refs=[])
    assert _errors(project, "metric-definition.schema.json", valid_metric(validity=empty_evidence))


def test_unvalidated_metric_is_a_legal_record(project: Path) -> None:
    """「還沒驗證過」是合法狀態。強制填只會生出為了通過檢查而寫的空話。"""
    assert _errors(project, "metric-definition.schema.json", _unvalidated_metric("recall_at_10")) == []

    honest = valid_metric(validity={
        "threshold_eligible": False,
        "limitations": ["標籤誤差率未量化"],
    })
    assert _errors(project, "metric-definition.schema.json", honest) == []


def test_validated_metric_passes_every_rule_shape(project: Path) -> None:
    """有資格的指標在哪一種規則下都通過。"""
    _project_with_evidence(project)
    write_record(project, "metrics", "recall_at_10", valid_metric(validity=_eligible_validity()))
    write_record(project, "definitions", "demo-exp", valid_definition())

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_secondary_metric_does_not_need_threshold_eligibility(project: Path) -> None:
    """次要指標是觀察用的，不承載判定，不必有資格。"""
    _project_with_evidence(project)
    write_record(project, "metrics", "recall_at_10", valid_metric(validity=_eligible_validity()))
    write_record(project, "metrics", "latency_ms", _unvalidated_metric("latency_ms"))
    write_record(
        project, "definitions", "demo-exp", valid_definition(secondary_metrics=["latency_ms"])
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_gate_threshold_metric_must_be_threshold_eligible(project: Path) -> None:
    """Compute Gate 的門檻也是門檻。掛在沒資格的指標上一樣要擋。"""
    _project_with_evidence(project)
    write_record(project, "metrics", "recall_at_10", valid_metric(validity=_eligible_validity()))
    write_record(project, "metrics", "latency_ms", _unvalidated_metric("latency_ms"))
    write_record(project, "definitions", "demo-exp", valid_definition(
        secondary_metrics=["latency_ms"],
        compute_cascade=[{
            "stage": "pilot",
            "level": "L1",
            "promotion": {
                "metric": "latency_ms", "source": "run", "field": "value",
                "run_scope": "all", "comparator": "<=", "threshold": 500,
            },
        }],
    ))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "threshold_eligible" in result.stdout
    assert "latency_ms" in result.stdout


def test_validity_evidence_ref_must_resolve(project: Path) -> None:
    """指不到的證據等於沒有證據。"""
    _project_with_evidence(project)
    write_record(project, "metrics", "recall_at_10", valid_metric(
        validity=_eligible_validity(evidence_refs=["docs/evidence/does-not-exist.md"])
    ))
    write_record(project, "definitions", "demo-exp", valid_definition())

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "does-not-exist.md" in result.stdout


# --- 可行性檢查 -------------------------------------------------------------


def test_feasibility_check_needs_command_evidence_and_verdict(project: Path) -> None:
    """四個欄位缺一不可：沒有命令就重跑不出來，沒有結論就不知道它在說什麼。"""
    complete = {
        "name": "gold 每卷供給足以支撐分層抽樣",
        "command": "demo gold-shape --by volume",
        "evidence_ref": EVIDENCE_REF,
        "passed": True,
    }
    assert _errors(project, "experiment-contract.schema.json",
                   valid_definition(feasibility_checks=[complete])) == []

    for missing in ("name", "command", "evidence_ref", "passed"):
        broken = dict(complete)
        broken.pop(missing)
        assert _errors(project, "experiment-contract.schema.json",
                       valid_definition(feasibility_checks=[broken])), missing


def test_feasibility_evidence_ref_must_resolve(project: Path) -> None:
    _project_with_evidence(project)
    write_record(project, "metrics", "recall_at_10", valid_metric(validity=_eligible_validity()))
    write_record(project, "definitions", "demo-exp", valid_definition(feasibility_checks=[{
        "name": "供給檢查",
        "command": "demo gold-shape --by volume",
        "evidence_ref": "docs/evidence/never-written.md",
        "passed": True,
    }]))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "never-written.md" in result.stdout


def test_recorded_feasibility_check_survives_the_contract_hash(project: Path) -> None:
    """可行性檢查在凍結範圍內。改了它就是改了 Contract，雜湊要跟著變。"""
    _project_with_evidence(project)
    write_record(project, "metrics", "recall_at_10", valid_metric(validity=_eligible_validity()))
    path = write_record(project, "definitions", "demo-exp", valid_definition())
    assert run_cli("contract-hash", str(path), "--write").returncode == 0
    before = json.loads(path.read_text(encoding="utf-8"))["contract_hash"]

    record = json.loads(path.read_text(encoding="utf-8"))
    record["feasibility_checks"] = [{
        "name": "供給檢查",
        "command": "demo gold-shape --by volume",
        "evidence_ref": EVIDENCE_REF,
        "passed": True,
    }]
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    result = run_cli("contract-hash", str(path))

    assert result.returncode == 1
    assert before in result.stdout


# --- 門檻資格只要求在「拿數字跟一條線比」的地方 --------------------------------


def test_interval_against_zero_does_not_require_threshold_eligibility(project: Path) -> None:
    """區間對 0 的判定自己帶著不確定性：儀器越吵，區間越寬，結論就越判不出來。

    這種規則不需要事先量出可偵測差距——真正需要的是「拿點估計跟一條非零的線比」
    的地方，那裡量測誤差會直接翻轉判定。
    """
    _project_with_evidence(project)
    write_record(project, "metrics", "recall_at_10", _unvalidated_metric("recall_at_10"))
    write_record(project, "definitions", "demo-exp", valid_definition())

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_non_zero_null_value_requires_threshold_eligibility(project: Path) -> None:
    """null value 不是 0，就是在宣告一個最小有意義差距，那需要量測誤差撐得住。"""
    _project_with_evidence(project)
    write_record(project, "metrics", "recall_at_10", _unvalidated_metric("recall_at_10"))
    plan = valid_definition()["analysis_plan"]
    plan["decision_rules"] = [{
        "id": "decision.primary", "estimand_ref": "effect.primary",
        "type": "superiority", "null_value": 0.05,
    }]
    write_record(project, "definitions", "demo-exp", valid_definition(analysis_plan=plan))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "threshold_eligible" in result.stdout
    assert "decision.primary" in result.stdout


def test_equivalence_margin_requires_threshold_eligibility(project: Path) -> None:
    """等價 margin 是最典型的門檻：誤差比 margin 大，判定就沒有意義。"""
    _project_with_evidence(project)
    write_record(project, "metrics", "recall_at_10", _unvalidated_metric("recall_at_10"))
    plan = valid_definition()["analysis_plan"]
    plan["decision_rules"] = [{
        "id": "decision.primary", "estimand_ref": "effect.primary", "type": "equivalence",
        "equivalence_margin": {
            "lower": -0.05, "upper": 0.05, "scale": "raw",
            "interval_confidence_level": 0.95, "interval_method": "percentile",
            "boundary": "exclusive",
        },
    }]
    write_record(project, "definitions", "demo-exp", valid_definition(analysis_plan=plan))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "threshold_eligible" in result.stdout
