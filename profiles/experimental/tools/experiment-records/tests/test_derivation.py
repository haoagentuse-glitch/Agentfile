"""Research Question Certificate 的確定性硬檢查。

這裡只驗證結構本身可判定的事。機制講得對不對是語意判斷，不在這層做，
也不得由這層放行——通過硬檢查只代表題目「可稽核」，不代表題目「正確」。
"""

from __future__ import annotations

from pathlib import Path

from helpers import (
    run_cli,
    valid_definition,
    valid_derivation,
    write_config,
    write_record,
)


def _project_with_configs(project: Path) -> None:
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")


def test_valid_derivation_passes(project: Path) -> None:
    _project_with_configs(project)
    write_record(project, "definitions", "demo-exp", valid_definition(derivation=valid_derivation()))

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_locked_contract_requires_a_derivation(project: Path) -> None:
    """lock 是開始花算力的那一刻；此時題目推導必須已可稽核。"""
    _project_with_configs(project)
    write_record(project, "definitions", "demo-exp", valid_definition(status="locked"))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "derivation" in result.stdout


def test_locked_contract_with_derivation_passes(project: Path) -> None:
    _project_with_configs(project)
    write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(status="locked", derivation=valid_derivation()),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_draft_contract_needs_no_derivation(project: Path) -> None:
    _project_with_configs(project)
    write_record(project, "definitions", "demo-exp", valid_definition())

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_duplicate_assumption_ids_are_rejected(project: Path) -> None:
    """failure update 與 claim audit 都靠 ID 指回 assumption；ID 重複就指不準。"""
    _project_with_configs(project)
    derivation = valid_derivation(
        assumptions=[
            {"id": "a1", "statement": "第一個前提", "status": "unverified"},
            {"id": "a1", "statement": "第二個前提", "status": "unverified"},
        ]
    )
    write_record(project, "definitions", "demo-exp", valid_definition(derivation=derivation))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "assumptions ID 重複：a1" in result.stdout


def test_duplicate_primitive_ids_are_rejected(project: Path) -> None:
    _project_with_configs(project)
    derivation = valid_derivation(
        primitives=[
            {"id": "coverage", "definition": "第一個定義"},
            {"id": "coverage", "definition": "第二個定義"},
        ]
    )
    write_record(project, "definitions", "demo-exp", valid_definition(derivation=derivation))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "primitives ID 重複：coverage" in result.stdout


def test_failure_update_must_point_at_an_existing_assumption(project: Path) -> None:
    _project_with_configs(project)
    derivation = valid_derivation(
        failure_update=[{"when": "recall 沒提升", "update_assumption_id": "a9", "to": "refuted"}]
    )
    write_record(project, "definitions", "demo-exp", valid_definition(derivation=derivation))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "指向不存在的 assumption 'a9'" in result.stdout


def test_novelty_claim_without_sources_is_rejected(project: Path) -> None:
    """沒有保存下來的來源就宣告新穎，是模型憑記憶判斷——證據上等於沒查。"""
    _project_with_configs(project)
    derivation = valid_derivation(novelty_status="novel_claimed", source_refs=[])
    write_record(project, "definitions", "demo-exp", valid_definition(derivation=derivation))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "未查證只能標 unverified" in result.stdout


def test_novelty_claim_with_saved_sources_passes(project: Path) -> None:
    _project_with_configs(project)
    write_config(project, "records/experiments/artifacts/prior-art.md", "# 查過的來源\n")
    derivation = valid_derivation(
        novelty_status="novel_claimed",
        source_refs=["records/experiments/artifacts/prior-art.md"],
    )
    write_record(project, "definitions", "demo-exp", valid_definition(derivation=derivation))

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_source_ref_must_resolve(project: Path) -> None:
    _project_with_configs(project)
    derivation = valid_derivation(source_refs=["records/experiments/artifacts/missing.md"])
    write_record(project, "definitions", "demo-exp", valid_definition(derivation=derivation))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "derivation.source_refs.0" in result.stdout


def test_mechanism_model_must_mention_the_treatment_variable(project: Path) -> None:
    """機制敘述沒提到實際被操弄的變因，代表這段機制跟這個實驗無關。"""
    _project_with_configs(project)
    derivation = valid_derivation(
        mechanism_model={"summary": "跟本實驗無關的機制", "variables": ["chunk_size"]}
    )
    write_record(project, "definitions", "demo-exp", valid_definition(derivation=derivation))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "未包含 treatment.variable 'top_k'" in result.stdout


def test_derivation_without_falsifier_is_rejected(project: Path) -> None:
    """沒有可證偽觀察的題目不該花算力。"""
    _project_with_configs(project)
    derivation = valid_derivation()
    del derivation["falsifier"]
    write_record(project, "definitions", "demo-exp", valid_definition(derivation=derivation))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "falsifier" in result.stdout


def test_derivation_without_mechanism_summary_is_rejected(project: Path) -> None:
    _project_with_configs(project)
    derivation = valid_derivation(mechanism_model={"variables": ["top_k"]})
    write_record(project, "definitions", "demo-exp", valid_definition(derivation=derivation))

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "summary" in result.stdout


def test_empty_assumptions_are_rejected(project: Path) -> None:
    _project_with_configs(project)
    write_record(
        project,
        "definitions",
        "demo-exp",
        valid_definition(derivation=valid_derivation(assumptions=[])),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "assumptions" in result.stdout
