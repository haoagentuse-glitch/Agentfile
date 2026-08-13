"""run 的階段、lineage、失敗與資源上限。

跑失敗是正式結果，不是缺資料；跑超過預算而沒有中止原因，代表預算不是真的預算。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from helpers import run_cli, valid_run, write_config, write_record


@pytest.fixture(autouse=True)
def _baseline_config(project: Path) -> None:
    """valid_run 的 config_ref 指到這個檔案；不建立的話每個測試都會先卡在 ref 解析。"""
    write_config(project, "records/experiments/configs/baseline.yaml")


def test_every_stage_is_expressible(project: Path) -> None:
    """pilot、tune、main、ablation、replication、diagnostic 都要能表示。"""
    for index, stage in enumerate(("pilot", "tune", "main", "ablation", "replication", "diagnostic")):
        overrides: dict[str, object] = {"run_id": f"demo-run-{index}", "stage": stage}
        if stage == "replication":
            overrides["parent_run_id"] = "demo-run-0"
        write_record(project, "runs", f"demo-run-{index}", valid_run(**overrides))

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_failed_run_is_expressible(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(
            status="invalid",
            invalid_reason="retriever 在第 40 筆查詢逾時",
            stage="pilot",
            failure={
                "class": "execution",
                "phase": "execution",
                "exit_code": 124,
                "retriable": True,
            },
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_failure_block_cannot_hide_behind_completed_status(project: Path) -> None:
    """有 failure 卻標 completed，就是用空成功偽裝失敗。"""
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(status="completed", failure={"class": "data", "phase": "data_load"}),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "status" in result.stdout


def test_unknown_failure_class_is_rejected(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(
            status="invalid",
            invalid_reason="不明原因",
            failure={"class": "看起來怪怪的", "phase": "execution"},
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "class" in result.stdout


def test_replication_must_name_its_parent(project: Path) -> None:
    write_record(project, "runs", "demo-run-1", valid_run(stage="replication"))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "stage=replication 必須指定 parent_run_id" in result.stdout


def test_retry_must_name_its_parent(project: Path) -> None:
    write_record(project, "runs", "demo-run-1", valid_run(attempt_kind="retry"))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "必須指定 parent_run_id" in result.stdout


def test_parent_run_must_exist(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(stage="replication", parent_run_id="does-not-exist"),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "指向不存在的 run" in result.stdout


def test_lineage_cycle_is_rejected(project: Path) -> None:
    write_record(project, "runs", "a", valid_run(run_id="a", parent_run_id="b"))
    write_record(project, "runs", "b", valid_run(run_id="b", parent_run_id="a"))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "循環 lineage" in result.stdout


def test_self_parent_is_rejected(project: Path) -> None:
    write_record(project, "runs", "a", valid_run(run_id="a", parent_run_id="a"))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "指向自己" in result.stdout


def test_valid_lineage_chain_passes(project: Path) -> None:
    write_record(project, "runs", "a", valid_run(run_id="a", stage="pilot"))
    write_record(
        project, "runs", "b", valid_run(run_id="b", stage="replication", parent_run_id="a")
    )
    write_record(
        project, "runs", "c", valid_run(run_id="c", stage="replication", parent_run_id="b")
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_exceeding_budget_without_abort_reason_is_rejected(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(duration_seconds=900, budget_limit={"max_wall_clock_seconds": 300}),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "超過 budget_limit.max_wall_clock_seconds=300" in result.stdout


def test_exceeding_sample_budget_without_abort_reason_is_rejected(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(resource_usage={"samples": 5000}, budget_limit={"max_samples": 100}),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "超過 budget_limit.max_samples=100" in result.stdout


def test_exceeding_budget_with_abort_reason_passes(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(
            duration_seconds=900,
            budget_limit={"max_wall_clock_seconds": 300},
            abort_reason="超出 pilot 預算後中止，保留已產出的部分結果",
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_run_within_budget_passes(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(
            duration_seconds=120,
            resource_usage={"cost_usd": 0.8, "samples": 100},
            budget_limit={"max_wall_clock_seconds": 300, "max_cost_usd": 2.0, "max_samples": 500},
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_completed_run_without_seed_or_nondeterminism_sources_warns(project: Path) -> None:
    """警告而非錯誤——不可重現的 run 仍是正式紀錄，但不該安靜通過。"""
    write_record(project, "runs", "demo-run-1", valid_run())

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "未宣告 seed，也未列出 nondeterminism_sources" in result.stdout


def test_declaring_nondeterminism_sources_clears_the_warning(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(seed=None, nondeterminism_sources=["生成模型 API 取樣不可固定"]),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "未宣告 seed" not in result.stdout


def test_component_identity_carries_prompt_hash(project: Path) -> None:
    """prompt 是最常被當成隱藏設定的東西；沒有 hash 就偵測不到 prompt 漂移。"""
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(
            seed=42,
            components={
                "retriever": {"name": "bm25", "version": "1.2.0"},
                "generator": {
                    "name": "answer-writer",
                    "model": "anthropic/claude-opus-5",
                    "prompt_id": "answer-writer@3",
                    "prompt_hash": "sha256:" + "b" * 64,
                    "temperature": 0,
                },
            },
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_malformed_component_prompt_hash_is_rejected(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(components={"generator": {"name": "answer-writer", "prompt_hash": "deadbeef"}}),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "prompt_hash" in result.stdout


def test_data_identity_requires_an_id(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(data_identity={"corpus_snapshot": {"hash": "sha256:abc"}}),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "id" in result.stdout


def test_data_identity_accepts_named_roles(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(
            seed=7,
            data_identity={
                "dataset": {"id": "corpus-a", "hash": "sha256:abc"},
                "evaluation_set": {"id": "eval-v3", "hash": "sha256:def"},
                "corpus_snapshot": {"id": "snap-2026-01-01"},
                "distractor_pool": {"id": "pool-1"},
            },
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_dirty_worktree_and_command_are_expressible(project: Path) -> None:
    write_record(
        project,
        "runs",
        "demo-run-1",
        valid_run(
            seed=1,
            code_commit="abc1234",
            dirty_worktree=True,
            command="python -m rag_lab pipeline run --stage pilot",
            environment="Linux 6.18 / Python 3.12",
            started_at="2026-01-01T00:00:00Z",
            finished_at="2026-01-01T00:02:00Z",
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
