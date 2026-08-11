from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from helpers import (
    run_cli,
    valid_claim,
    valid_comparison,
    valid_definition,
    valid_run,
    write_config,
    write_record,
)


def test_help_lists_validate_subcommand() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "validate" in result.stdout


def test_validate_rejects_nonexistent_target(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    result = run_cli("validate", str(missing))
    assert result.returncode == 2
    assert str(missing) in result.stderr or str(missing) in result.stdout


def test_validate_passes_for_valid_project(project: Path) -> None:
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")
    write_record(project, "definitions", "demo-exp", valid_definition())
    write_record(project, "runs", "demo-run-1", valid_run())
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(project, "claims", "demo-claim", valid_claim())

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ERROR" not in result.stdout
    assert result.stdout.count("PASS") >= 4


def test_validate_accepts_single_record_file(project: Path) -> None:
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")
    record_path = write_record(project, "definitions", "demo-exp", valid_definition())

    result = run_cli("validate", str(record_path))

    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_accepts_records_experiments_root_as_target(project: Path) -> None:
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")
    write_record(project, "definitions", "demo-exp", valid_definition())

    result = run_cli("validate", str(project / "records" / "experiments"))

    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_reports_missing_required_field(project: Path) -> None:
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")
    definition = valid_definition()
    del definition["primary_metric"]
    write_record(project, "definitions", "demo-exp", definition)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "primary_metric" in result.stdout


def test_validate_rejects_undeclared_additional_property(project: Path) -> None:
    """驗證是完整 Draft 2020-12（含 additionalProperties: false），
    不是只檢 required/enum 的簡化版——這是舊版 experiment_lint.py 抓不到的錯誤。"""
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")
    definition = valid_definition(unexpected_field="不該存在的欄位")
    write_record(project, "definitions", "demo-exp", definition)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "unexpected_field" in result.stdout


def test_validate_enforces_conditional_schema_rule(project: Path) -> None:
    """run-envelope 的 allOf/if-then：status=invalid 時必填 invalid_reason。
    舊版 experiment_lint.py 的遞迴 required/enum 檢查完全不處理 allOf，這裡驗證新
    validator 真的在跑完整 Draft 2020-12（含條件式 schema），不是重新實作同一套簡化邏輯。"""
    run = valid_run(status="invalid")
    write_record(project, "runs", "demo-run-1", run)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "invalid_reason" in result.stdout


def test_validate_rejects_unknown_schema_type(project: Path) -> None:
    """record 檔案所在目錄不是七個已知類型之一——沒有對應 schema，必須明確拒絕，
    不能靜默跳過或憑空套用其他 schema。"""
    record_path = write_record(project, "unknown-type", "mystery", {"anything": "goes"})

    result = run_cli("validate", str(record_path))

    assert result.returncode == 1
    assert "unknown-type" in result.stdout


def test_validate_rejects_record_outside_records_root(project: Path) -> None:
    outside = project / "other" / "runs" / "demo-run.json"
    outside.parent.mkdir(parents=True)
    outside.write_text("{}", encoding="utf-8")

    result = run_cli("validate", str(outside))

    assert result.returncode == 2
    assert "records/experiments" in result.stderr


def test_validate_rejects_invalid_schema(project: Path) -> None:
    schema = project / "records" / "experiments" / "schemas" / "run-envelope.schema.json"
    schema.write_text('{"type": 42}', encoding="utf-8")
    write_record(project, "runs", "demo-run-1", valid_run())

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "run-envelope.schema.json" in result.stdout
    assert "本身無效" in result.stdout


def test_validate_applies_ref_rule_to_new_schema_field(project: Path) -> None:
    schema_path = (
        project / "records" / "experiments" / "schemas" / "run-envelope.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["properties"]["artifact_ref"] = {"type": "string"}
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    run = valid_run(artifact_ref="../outside.json")
    write_record(project, "runs", "demo-run-1", run)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "artifact_ref" in result.stdout
    assert ".." in result.stdout


def test_validate_rejects_ref_with_dotdot_traversal(project: Path) -> None:
    definition = valid_definition(
        baseline={
            "description": "baseline",
            "config_ref": "../outside/baseline.yaml",
        }
    )
    write_record(project, "definitions", "demo-exp", definition)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert ".." in result.stdout


def test_validate_rejects_posix_absolute_ref(project: Path) -> None:
    definition = valid_definition(
        baseline={"description": "baseline", "config_ref": "/etc/passwd"}
    )
    write_record(project, "definitions", "demo-exp", definition)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "/etc/passwd" in result.stdout


def test_validate_rejects_windows_drive_ref(project: Path) -> None:
    definition = valid_definition(
        baseline={"description": "baseline", "config_ref": "C:/Users/me/baseline.yaml"}
    )
    write_record(project, "definitions", "demo-exp", definition)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "C:/Users/me/baseline.yaml" in result.stdout


def test_validate_rejects_missing_ref_target(project: Path) -> None:
    definition = valid_definition()  # config_ref 指到的檔案沒有實際建立
    write_record(project, "definitions", "demo-exp", definition)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "baseline.yaml" in result.stdout


@pytest.mark.skipif(sys.platform == "win32", reason="symlink escape 測試用 POSIX symlink")
def test_validate_rejects_ref_symlink_escape(
    project: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    # project 本身就是一個 tmp_path，這裡另外要一個跟它不同、非子孫關係的目錄，
    # 才能真正測到「跳脫 project root」，不是自己包自己。
    outside = tmp_path_factory.mktemp("outside")
    secret = outside / "secret.yaml"
    secret.write_text("secret: true\n", encoding="utf-8")

    link_dir = project / "records" / "experiments" / "configs"
    link_dir.mkdir(parents=True)
    os.symlink(secret, link_dir / "baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")

    definition = valid_definition()
    write_record(project, "definitions", "demo-exp", definition)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "config_ref" in result.stdout
