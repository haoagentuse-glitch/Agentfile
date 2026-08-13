from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from helpers import (
    run_cli,
    valid_claim,
    valid_comparison,
    valid_definition,
    valid_lifecycle,
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
    assert "\n錯誤" not in f"\n{result.stdout}"
    assert result.stdout.count("通過") >= 4


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
    不是只檢 required/enum 的簡化版——這是舊版簡化 validator 抓不到的錯誤。"""
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")
    definition = valid_definition(unexpected_field="不該存在的欄位")
    write_record(project, "definitions", "demo-exp", definition)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "unexpected_field" in result.stdout


def test_validate_enforces_conditional_schema_rule(project: Path) -> None:
    """run-envelope 的 allOf/if-then：status=invalid 時必填 invalid_reason。
    舊版簡化 validator 的遞迴 required/enum 檢查完全不處理 allOf，這裡驗證新
    validator 真的在跑完整 Draft 2020-12（含條件式 schema），不是重新實作同一套簡化邏輯。"""
    run = valid_run(status="invalid")
    write_record(project, "runs", "demo-run-1", run)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "invalid_reason" in result.stdout


def test_validate_rejects_unknown_schema_type(project: Path) -> None:
    """record 檔案所在目錄不是八個已知類型之一——沒有對應 schema，必須明確拒絕，
    不能靜默跳過或憑空套用其他 schema。"""
    record_path = write_record(project, "unknown-type", "mystery", {"anything": "goes"})

    result = run_cli("validate", str(record_path))

    assert result.returncode == 1
    assert "unknown-type" in result.stdout


def test_validate_rejects_unknown_record_directory_in_project(project: Path) -> None:
    write_record(project, "unknown-type", "mystery", {"anything": "goes"})

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "unknown-type" in result.stdout


def test_validate_checks_schemas_without_records(project: Path) -> None:
    schema = project / "records" / "experiments" / "schemas" / "run-envelope.schema.json"
    schema.write_text('{"type": 42}', encoding="utf-8")

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "run-envelope.schema.json" in result.stdout
    assert "本身無效" in result.stdout


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
    schema["properties"]["artifact_location"] = {
        "type": "string",
        "format": "project-ref",
    }
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    run = valid_run(artifact_location="../outside.json")
    write_record(project, "runs", "demo-run-1", run)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "artifact_location" in result.stdout
    assert ".." in result.stdout


def test_validate_prints_glass_box_summary(project: Path) -> None:
    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "命令：uv run --project .agents/tools/experiment-records python -m experiment_records validate" in result.stdout
    assert f"輸入：{project.resolve()}" in result.stdout
    assert "Schema：" in result.stdout
    assert "Commit：" in result.stdout


def test_validate_marks_dirty_project_commit(project: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=project,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    git("init")
    git("config", "user.name", "Experiment Records Test")
    git("config", "user.email", "experiment-records@example.invalid")
    git("add", ".")
    git("commit", "-m", "建立測試專案")

    schema = project / "records" / "experiments" / "schemas" / "claim.schema.json"
    schema.write_text(schema.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "-dirty" in result.stdout


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


def test_validate_rejects_lifecycle_that_skips_pilot(project: Path) -> None:
    lifecycle = {
        "experiment_id": "demo-exp",
        "current_state": "locked",
        "history": [
            {
                "from_state": None,
                "to_state": "draft",
                "occurred_at": "2026-01-01T00:00:00Z",
                "reason": "建立實驗",
                "evidence_refs": [],
            },
            {
                "from_state": "draft",
                "to_state": "locked",
                "occurred_at": "2026-01-01T00:01:00Z",
                "reason": "未經 preflight 直接鎖定",
                "evidence_refs": [],
            },
        ],
        "updated_at": "2026-01-01T00:01:00Z",
    }
    write_record(project, "lifecycles", "demo-exp", lifecycle)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "非法生命週期轉移：draft -> locked" in result.stdout


def test_validate_accepts_complete_lifecycle(project: Path) -> None:
    lifecycle = valid_lifecycle(
        "draft",
        "ready_to_lock",
        "locked",
        "pilot_running",
        "promoted",
        "main_running",
        "awaiting_comparison",
        "awaiting_claim",
        "awaiting_review",
        "accepted",
    )
    write_record(project, "lifecycles", "demo-exp", lifecycle)

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "生命週期轉移合法" in result.stdout


@pytest.mark.parametrize(
    ("states", "illegal_transition"),
    [
        (
            ("draft", "ready_to_lock", "locked", "main_running"),
            "locked -> main_running",
        ),
        (
            (
                "draft",
                "ready_to_lock",
                "locked",
                "pilot_running",
                "promoted",
                "main_running",
                "awaiting_claim",
            ),
            "main_running -> awaiting_claim",
        ),
        (
            (
                "draft",
                "ready_to_lock",
                "locked",
                "pilot_running",
                "promoted",
                "main_running",
                "awaiting_comparison",
                "awaiting_claim",
                "accepted",
            ),
            "awaiting_claim -> accepted",
        ),
    ],
    ids=["skip-pilot", "skip-comparison", "skip-audit"],
)
def test_validate_rejects_skipped_lifecycle_stage(
    project: Path, states: tuple[str, ...], illegal_transition: str
) -> None:
    write_record(project, "lifecycles", "demo-exp", valid_lifecycle(*states))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert f"非法生命週期轉移：{illegal_transition}" in result.stdout


def test_validate_rejects_revise_without_updated_field_and_evidence(
    project: Path,
) -> None:
    lifecycle = valid_lifecycle(
        "draft",
        "ready_to_lock",
        "locked",
        "pilot_running",
        "promoted",
        "main_running",
        "awaiting_comparison",
        "awaiting_claim",
        "awaiting_review",
        "revise",
    )
    write_record(project, "lifecycles", "demo-exp", lifecycle)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "updated_definition_fields" in result.stdout
    assert "evidence_refs" in result.stdout


def test_validate_accepts_revise_with_updated_field_and_evidence(project: Path) -> None:
    evidence = write_record(
        project, "artifacts", "new-evidence", {"finding": "反例成立"}
    )
    lifecycle = valid_lifecycle(
        "draft",
        "ready_to_lock",
        "locked",
        "pilot_running",
        "promoted",
        "main_running",
        "awaiting_comparison",
        "awaiting_claim",
        "awaiting_review",
        "revise",
    )
    lifecycle["history"][-1]["updated_definition_fields"] = ["/hypothesis"]
    lifecycle["history"][-1]["evidence_refs"] = [
        str(evidence.relative_to(project))
    ]
    write_record(project, "lifecycles", "demo-exp", lifecycle)

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "生命週期轉移合法" in result.stdout


@pytest.mark.parametrize(
    "states",
    [
        ("draft", "preflight_failed"),
        (
            "draft",
            "ready_to_lock",
            "locked",
            "pilot_running",
            "pilot_failed",
        ),
        (
            "draft",
            "ready_to_lock",
            "locked",
            "pilot_running",
            "pilot_inconclusive",
        ),
        (
            "draft",
            "ready_to_lock",
            "locked",
            "pilot_running",
            "promoted",
            "main_running",
            "execution_failed",
        ),
        (
            "draft",
            "ready_to_lock",
            "locked",
            "pilot_running",
            "promoted",
            "main_running",
            "awaiting_comparison",
            "confounded",
        ),
        (
            "draft",
            "ready_to_lock",
            "locked",
            "pilot_running",
            "promoted",
            "main_running",
            "awaiting_comparison",
            "awaiting_claim",
            "awaiting_review",
            "inconclusive",
        ),
    ],
    ids=[
        "preflight-failed",
        "pilot-failed",
        "pilot-inconclusive",
        "execution-failed",
        "confounded",
        "inconclusive",
    ],
)
def test_validate_accepts_formal_terminal_state(
    project: Path, states: tuple[str, ...]
) -> None:
    write_record(project, "lifecycles", "demo-exp", valid_lifecycle(*states))

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_rejects_transition_after_terminal_state(project: Path) -> None:
    lifecycle = valid_lifecycle("draft", "preflight_failed", "ready_to_lock")
    write_record(project, "lifecycles", "demo-exp", lifecycle)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "非法生命週期轉移：preflight_failed -> ready_to_lock" in result.stdout


def test_validate_uses_lifecycle_schema_as_transition_source(project: Path) -> None:
    schema_path = (
        project
        / "records"
        / "experiments"
        / "schemas"
        / "lifecycle-state.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["x-allowed-transitions"]["draft"].append("locked")
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    write_record(
        project,
        "lifecycles",
        "demo-exp",
        valid_lifecycle("draft", "locked"),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_rejects_incomplete_lifecycle_transition_table(project: Path) -> None:
    schema_path = (
        project
        / "records"
        / "experiments"
        / "schemas"
        / "lifecycle-state.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    del schema["x-allowed-transitions"]["draft"]
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "轉移表必須為每個 state 定義出口" in result.stdout
