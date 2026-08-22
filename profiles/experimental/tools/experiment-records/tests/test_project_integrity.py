"""Project integrity：contract hash、metric 連結、機械失敗的稽核與 operation scope。

只走公開入口：CLI 與 `load_project(root) -> ProjectSnapshot`。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiment_records.project_snapshot import load_project
from helpers import (
    run_cli,
    valid_audit,
    valid_claim,
    valid_comparison,
    valid_definition,
    valid_derivation,
    valid_metric,
    write_config,
    write_record,
)

# valid_definition() 的 RFC 8785 正規形式，逐字寫死。
# 這是獨立的比對來源：鍵序、無空白、中文不轉義、整數不加小數點，任何一項變了都會失敗。
CANONICAL_DEFINITION = (
    '{"abort_rule":"guardrail 超標立即中止",'
    '"baseline":{"config_ref":"records/experiments/configs/baseline.yaml",'
    '"description":"baseline pipeline"},'
    '"compute_budget":{"pilot_max_minutes":5,"pilot_max_samples":100},'
    '"controlled_variables":["dataset"],'
    '"created_at":"2026-01-01T00:00:00Z",'
    '"decision_rule":"recall 提升至少 0.05 視為成功",'
    '"evidence_policy":{"eligible_run_stages":["pilot","main","replication"]},'
    '"experiment_id":"demo-exp",'
    '"hypothesis":"提高 top_k 會提升 recall",'
    '"primary_metric":"recall_at_10",'
    '"question":"top_k 提高是否讓 recall 提升？",'
    '"status":"draft",'
    '"treatment":{"config_ref":"records/experiments/configs/treatment.yaml",'
    '"description":"treatment pipeline","variable":"top_k"}}'
)


def _digest(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _configs(project: Path) -> None:
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")


def _definition_path(project: Path) -> Path:
    return project / "records" / "experiments" / "definitions" / "demo-exp.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --- contract hash（Issue #1）-------------------------------------------------


def test_contract_hash_matches_rfc8785_canonical_form(project: Path) -> None:
    _configs(project)
    path = write_record(project, "definitions", "demo-exp", valid_definition())

    result = run_cli("contract-hash", str(path))

    assert result.returncode == 1, result.stdout + result.stderr
    assert _digest(CANONICAL_DEFINITION) in result.stdout


def test_contract_hash_glass_box_command_is_the_public_entry(project: Path) -> None:
    """回溯性摘要必須指向使用者真的能重跑的那一行，不是內部函式呼叫。"""
    _configs(project)
    path = write_record(project, "definitions", "demo-exp", valid_definition())

    result = run_cli("contract-hash", str(path))

    assert "命令：python -m experiment_records contract-hash " + str(path) in result.stdout
    assert ".agents/tools/experiment-records" not in result.stdout


def test_contract_hash_uses_ecmascript_number_form(project: Path) -> None:
    _configs(project)
    definition = valid_definition(
        compute_budget={"pilot_max_minutes": 1e-7, "pilot_max_samples": 100}
    )
    path = write_record(project, "definitions", "demo-exp", definition)
    canonical = CANONICAL_DEFINITION.replace(
        '"pilot_max_minutes":5', '"pilot_max_minutes":1e-7'
    )

    result = run_cli("contract-hash", str(path))

    assert _digest(canonical) in result.stdout


def test_contract_hash_is_key_order_independent(project: Path) -> None:
    _configs(project)
    definition = valid_definition()
    reordered = dict(reversed(list(definition.items())))
    path = write_record(project, "definitions", "demo-exp", reordered)

    result = run_cli("contract-hash", str(path))

    assert _digest(CANONICAL_DEFINITION) in result.stdout


def test_contract_hash_write_updates_only_that_field(project: Path) -> None:
    _configs(project)
    path = write_record(project, "definitions", "demo-exp", valid_definition())
    before = _read(path)

    written = run_cli("contract-hash", str(path), "--write")

    assert written.returncode == 0, written.stdout + written.stderr
    assert "old" in written.stdout and "new" in written.stdout
    after = _read(path)
    assert after.pop("contract_hash") == _digest(CANONICAL_DEFINITION)
    assert after == before


def test_contract_hash_excludes_the_field_itself(project: Path) -> None:
    """填進去的雜湊不得影響下一次計算，否則永遠對不上自己。"""
    _configs(project)
    path = write_record(project, "definitions", "demo-exp", valid_definition())
    run_cli("contract-hash", str(path), "--write")

    verified = run_cli("contract-hash", str(path))

    assert verified.returncode == 0, verified.stdout + verified.stderr


def test_contract_hash_changes_when_content_changes(project: Path) -> None:
    _configs(project)
    path = write_record(project, "definitions", "demo-exp", valid_definition())
    run_cli("contract-hash", str(path), "--write")
    record = _read(path)
    record["hypothesis"] = "改過的假說"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    result = run_cli("contract-hash", str(path))

    assert result.returncode == 1
    assert "expected" in result.stdout
    assert "actual" in result.stdout


def test_contract_hash_rejects_legacy_prefixed_value(project: Path) -> None:
    """舊格式沒有相容層。帶 sha256: 前綴的值一律判為不符。"""
    _configs(project)
    path = write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(contract_hash=f"sha256:{_digest(CANONICAL_DEFINITION)}"),
    )

    result = run_cli("contract-hash", str(path))

    assert result.returncode == 1


def test_contract_hash_rejects_duplicate_top_level_key(tmp_path: Path) -> None:
    path = tmp_path / "duplicate-top-level.json"
    path.write_text('{"a":1,"a":2}', encoding="utf-8")

    result = run_cli("contract-hash", str(path))

    assert result.returncode == 1
    assert "重複" in result.stderr
    assert "expected" not in result.stdout


def test_contract_hash_rejects_duplicate_nested_key(tmp_path: Path) -> None:
    path = tmp_path / "duplicate-nested.json"
    path.write_text('{"nested":{"a":1,"a":2}}', encoding="utf-8")

    result = run_cli("contract-hash", str(path))

    assert result.returncode == 1
    assert "重複" in result.stderr
    assert "expected" not in result.stdout


def test_validate_reports_record_with_duplicate_key(project: Path) -> None:
    path = project / "records" / "experiments" / "definitions" / "duplicate.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"experiment_id":"demo-exp","experiment_id":"other-exp"}',
        encoding="utf-8",
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "重複" in result.stdout


def test_validate_accepts_locked_contract_with_correct_hash(project: Path) -> None:
    _configs(project)
    path = write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(status="locked", derivation=valid_derivation()),
    )
    assert run_cli("contract-hash", str(path), "--write").returncode == 0

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_rejects_locked_contract_with_stale_hash(project: Path) -> None:
    _configs(project)
    path = write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(status="locked", derivation=valid_derivation()),
    )
    run_cli("contract-hash", str(path), "--write")
    record = _read(path)
    record["decision_rule"] = "lock 之後偷改判準"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "contract_hash" in result.stdout


def test_validate_rejects_locked_contract_without_hash(project: Path) -> None:
    _configs(project)
    write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(status="locked", derivation=valid_derivation()),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "contract_hash" in result.stdout


# --- metric 定義連結（Issue #13）----------------------------------------------


def test_validate_rejects_primary_metric_without_definition(project: Path) -> None:
    _configs(project)
    write_record(
        project, "definitions", "demo-exp", valid_definition(primary_metric="ghost_metric")
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "ghost_metric" in result.stdout
    assert "primary_metric" in result.stdout


def test_validate_rejects_secondary_metric_without_definition(project: Path) -> None:
    _configs(project)
    write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(secondary_metrics=["latency_ms", "ghost_metric"]),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "ghost_metric" in result.stdout
    assert "secondary_metrics" in result.stdout


def test_validate_accepts_metrics_that_resolve_to_definitions(project: Path) -> None:
    _configs(project)
    write_record(project, "metrics", "custom_score", valid_metric(name="custom_score"))
    write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(primary_metric="custom_score", secondary_metrics=["latency_ms"]),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_metric_definition_is_matched_by_name_not_filename(project: Path) -> None:
    _configs(project)
    write_record(project, "metrics", "any-file-name", valid_metric(name="custom_score"))
    write_record(
        project, "definitions", "demo-exp", valid_definition(primary_metric="custom_score")
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


# --- 機械失敗的稽核（Issue #5）------------------------------------------------


def _mechanical_failure_project(project: Path) -> None:
    """一份誠實記錄下來的機械失敗稽核，Contract 要求 second_model 審核。"""
    _configs(project)
    write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(review_policy={"required_reviewer_kind": "second_model"}),
    )
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(project, "claims", "demo-claim", valid_claim(status="refuted"))
    write_record(
        project,
        "audits",
        "demo-audit",
        valid_audit(
            mechanical={
                "reference_exists": True,
                "comparison_valid": True,
                "metric_exists": True,
                "direction_matches": False,
                "magnitude_matches": None,
                "mechanical_pass": False,
            },
            scope_verdict="unsupported",
            scope_reasoning="機械檢查沒過，不需要再判斷 scope",
            final_verdict="unsupported",
        ),
    )


def test_mechanical_failure_does_not_require_reviewer_identity(project: Path) -> None:
    _mechanical_failure_project(project)

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "review_independence" not in result.stdout


def test_mechanical_pass_still_requires_reviewer_identity(project: Path) -> None:
    _configs(project)
    write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(review_policy={"required_reviewer_kind": "second_model"}),
    )
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(project, "claims", "demo-claim", valid_claim())
    write_record(project, "audits", "demo-audit", valid_audit())

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "review_independence" in result.stdout


def test_recorded_independence_must_stay_coherent_after_mechanical_failure(
    project: Path,
) -> None:
    """不適用不等於免檢。已經填了的欄位仍然不得自相矛盾。"""
    _mechanical_failure_project(project)
    audit_path = project / "records" / "experiments" / "audits" / "demo-audit.json"
    audit = _read(audit_path)
    audit["review_independence"] = {"independent": True, "reviewer_kind": "same_context"}
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "same_context" in result.stdout


def test_mechanical_failure_still_caps_the_verdict(project: Path) -> None:
    """結論強度的檢查不受影響。"""
    _mechanical_failure_project(project)
    audit_path = project / "records" / "experiments" / "audits" / "demo-audit.json"
    audit = _read(audit_path)
    audit["final_verdict"] = "fully_supported"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "final_verdict" in result.stdout


# --- operation scope（transition 只看目標 experiment）---------------------------


def _unrelated_broken_experiment(project: Path) -> None:
    write_record(
        project,
        "definitions",
        "other-exp",
        valid_definition(experiment_id="other-exp", primary_metric="ghost_metric"),
    )


def test_transition_is_not_blocked_by_an_unrelated_experiment(project: Path) -> None:
    _configs(project)
    write_record(project, "definitions", "demo-exp", valid_definition())
    _unrelated_broken_experiment(project)

    result = run_cli(
        "transition", str(project), "demo-exp", "draft",
        "--reason", "建立實驗", "--occurred-at", "2026-01-01T00:00:00Z",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_transition_is_blocked_by_the_target_experiment(project: Path) -> None:
    _configs(project)
    write_record(
        project, "definitions", "demo-exp", valid_definition(primary_metric="ghost_metric")
    )

    result = run_cli(
        "transition", str(project), "demo-exp", "draft",
        "--reason", "建立實驗", "--occurred-at", "2026-01-01T00:00:00Z",
    )

    assert result.returncode == 1
    assert "ghost_metric" in result.stderr


def test_validate_still_reports_every_experiment(project: Path) -> None:
    """validate 的範圍不變：全專案。縮小的只有 transition。"""
    _configs(project)
    write_record(project, "definitions", "demo-exp", valid_definition())
    _unrelated_broken_experiment(project)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "other-exp" in result.stdout


# --- load_project seam --------------------------------------------------------


def test_load_project_indexes_records_by_id(project: Path) -> None:
    _configs(project)
    write_record(project, "definitions", "demo-exp", valid_definition())
    write_record(project, "metrics", "any-file-name", valid_metric(name="custom_score"))

    snapshot = load_project(project)

    assert snapshot.record("definitions", "demo-exp") is not None
    assert snapshot.record("metrics", "custom_score") is not None
    assert snapshot.record("definitions", "missing-exp") is None


def test_closure_keeps_unrelated_experiments_out(project: Path) -> None:
    _configs(project)
    write_record(project, "definitions", "demo-exp", valid_definition())
    write_record(project, "claims", "demo-claim", valid_claim())
    write_record(project, "audits", "demo-audit", valid_audit())
    write_record(project, "definitions", "other-exp", valid_definition(experiment_id="other-exp"))

    labels = {record.label for record in load_project(project).closure("demo-exp")}

    assert "records/experiments/definitions/demo-exp.json" in labels
    assert "records/experiments/claims/demo-claim.json" in labels
    assert "records/experiments/audits/demo-audit.json" in labels
    assert "records/experiments/definitions/other-exp.json" not in labels


def test_closure_includes_the_metric_definitions_a_contract_cites(project: Path) -> None:
    _configs(project)
    write_record(project, "metrics", "custom_score", valid_metric(name="custom_score"))
    write_record(
        project, "definitions", "demo-exp", valid_definition(primary_metric="custom_score")
    )

    labels = {record.label for record in load_project(project).closure("demo-exp")}

    assert "records/experiments/metrics/custom_score.json" in labels
