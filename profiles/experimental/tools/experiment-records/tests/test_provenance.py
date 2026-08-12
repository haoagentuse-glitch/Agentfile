"""共用 producer 區塊：跨檔 $ref 可解析、agent 產物必須可回溯 model 與 prompt、
provenance 裡的 input_refs 跟其他 project-ref 受同一套 containment 規則管。"""

from __future__ import annotations

from pathlib import Path

from helpers import (
    run_cli,
    valid_audit,
    valid_claim,
    valid_comparison,
    valid_definition,
    write_config,
    write_record,
)


def _agent_producer(**overrides: object) -> dict:
    producer = {
        "kind": "software_agent",
        "name": "research-question-builder",
        "model": "anthropic/claude-opus-5",
        "prompt_id": "research-question-builder@1",
        "prompt_hash": "sha256:" + "a" * 64,
        "created_at": "2026-01-01T00:00:00Z",
    }
    producer.update(overrides)
    return producer


def _project_with_configs(project: Path) -> None:
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")


def test_cross_file_ref_resolves_and_accepts_agent_producer(project: Path) -> None:
    _project_with_configs(project)
    write_record(project, "definitions", "demo-exp", valid_definition(producer=_agent_producer()))

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "provenance.schema.json: Schema 有效" in result.stdout


def test_software_agent_without_model_is_rejected(project: Path) -> None:
    """agent 產出卻回溯不到 model／prompt 版本，稽核就無法重現當初的判斷。"""
    _project_with_configs(project)
    producer = _agent_producer()
    del producer["model"]
    write_record(project, "definitions", "demo-exp", valid_definition(producer=producer))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "model" in result.stdout


def test_software_agent_without_prompt_id_is_rejected(project: Path) -> None:
    _project_with_configs(project)
    producer = _agent_producer()
    del producer["prompt_id"]
    write_record(project, "definitions", "demo-exp", valid_definition(producer=producer))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "prompt_id" in result.stdout


def test_deterministic_program_needs_no_model(project: Path) -> None:
    """compare_runs.py 這類不含 LLM 的程式輸出可由同一輸入重算，不需要 model／prompt。"""
    _project_with_configs(project)
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(
        project,
        "claims",
        "demo-claim",
        valid_claim(
            producer={
                "kind": "deterministic_program",
                "name": "compare_runs.py",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_malformed_prompt_hash_is_rejected(project: Path) -> None:
    _project_with_configs(project)
    write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(producer=_agent_producer(prompt_hash="abc123")),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "prompt_hash" in result.stdout


def test_producer_input_ref_must_resolve(project: Path) -> None:
    """provenance 裡的 ref 跟其他 project-ref 走同一套解析——$ref 之後不得漏掉檢查。"""
    _project_with_configs(project)
    write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(producer=_agent_producer(input_refs=["records/experiments/artifacts/missing.jsonl"])),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "producer.input_refs.0" in result.stdout


def test_producer_input_ref_cannot_escape_project_root(project: Path) -> None:
    _project_with_configs(project)
    write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(producer=_agent_producer(input_refs=["../outside.jsonl"])),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert ".." in result.stdout


def test_audit_producer_records_the_reviewing_agent(project: Path) -> None:
    _project_with_configs(project)
    write_record(project, "comparisons", "demo-comparison", valid_comparison())
    write_record(project, "claims", "demo-claim", valid_claim())
    write_record(
        project,
        "audits",
        "demo-audit",
        valid_audit(producer=_agent_producer(name="evidence-reviewer", prompt_id="evidence-reviewer@1")),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_version_unresolved_requires_the_identifier_actually_seen(project: Path) -> None:
    """標了 version_unresolved 卻連識別符都沒記，等於沒有 provenance。"""
    _project_with_configs(project)
    producer = _agent_producer(version_unresolved=True)
    del producer["model"]
    write_record(project, "definitions", "demo-exp", valid_definition(producer=producer))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "model" in result.stdout
