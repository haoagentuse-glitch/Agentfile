from pathlib import Path

from helpers import run_cli, valid_definition, write_config, write_record


def test_controlled_variable_difference_blocks_contract(project: Path) -> None:
    write_config(
        project,
        "records/experiments/configs/baseline.yaml",
        "dataset: corpus-a\ntop_k: 5\nseed: 42\n",
    )
    write_config(
        project,
        "records/experiments/configs/treatment.yaml",
        "dataset: corpus-b\ntop_k: 10\nseed: 42\n",
    )
    write_record(project, "definitions", "demo-exp", valid_definition())

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "controlled_variable 'dataset' 實際不同" in result.stdout


def test_undeclared_config_difference_blocks_contract(project: Path) -> None:
    write_config(
        project,
        "records/experiments/configs/baseline.yaml",
        "dataset: corpus-a\ntop_k: 5\nmodel: old\nseed: 42\n",
    )
    write_config(
        project,
        "records/experiments/configs/treatment.yaml",
        "dataset: corpus-a\ntop_k: 10\nmodel: new\nseed: 42\n",
    )
    write_record(project, "definitions", "demo-exp", valid_definition())

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "未宣告的設定差異 'model'" in result.stdout
