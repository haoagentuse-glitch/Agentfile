"""comparison-result 的三個判斷必須分開表示，而且只由程式算。

structurally_comparable、controlled_variables_match、confounded 問的是不同問題。
把它們併成一個布林值，就沒辦法回答「為什麼不能引用這次比較」。
"""

from __future__ import annotations

from pathlib import Path

from helpers import run_cli, valid_comparison, write_record


def test_valid_comparison_passes(project: Path) -> None:
    write_record(project, "comparisons", "demo-comparison", valid_comparison())

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_structurally_comparable_is_required(project: Path) -> None:
    comparison = valid_comparison()
    del comparison["structurally_comparable"]
    write_record(project, "comparisons", "demo-comparison", comparison)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "structurally_comparable" in result.stdout


def test_controlled_variables_match_is_required(project: Path) -> None:
    comparison = valid_comparison()
    del comparison["controlled_variables_match"]
    write_record(project, "comparisons", "demo-comparison", comparison)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "controlled_variables_match" in result.stdout


def test_invalid_but_not_confounded_is_expressible(project: Path) -> None:
    """沒有共同基準可比，跟條件沒守住，是兩種不同的失敗。"""
    write_record(
        project,
        "comparisons",
        "demo-comparison",
        valid_comparison(
            structurally_comparable=False,
            controlled_variables_match=True,
            comparison_valid=False,
            confounded=False,
            notes=["沒有任何指標在兩邊都存在且定義一致，這次比較沒有共同基準"],
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_every_difference_category_is_expressible(project: Path) -> None:
    """config、data、model、prompt、evaluator 的差異都要能具名列出。"""
    differences = [
        {"category": category, "key": f"{category}_key", "run_a_value": "a",
         "run_b_value": "b", "severity": "blocking", "declared": False}
        for category in ("config", "data", "model", "prompt", "evaluator", "sample", "unknown")
    ]
    write_record(
        project,
        "comparisons",
        "demo-comparison",
        valid_comparison(
            differences=differences,
            controlled_variables_match=False,
            comparison_valid=False,
            confounded=True,
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_unknown_difference_category_is_rejected(project: Path) -> None:
    write_record(
        project,
        "comparisons",
        "demo-comparison",
        valid_comparison(
            differences=[{
                "category": "隨便一種", "key": "k", "run_a_value": 1,
                "run_b_value": 2, "severity": "blocking",
            }]
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "category" in result.stdout


def test_difference_without_severity_is_rejected(project: Path) -> None:
    """沒有嚴重度就無法分辨「這正是我們要測的變化」跟「這讓效應無法歸因」。"""
    write_record(
        project,
        "comparisons",
        "demo-comparison",
        valid_comparison(
            differences=[{"category": "config", "key": "k", "run_a_value": 1, "run_b_value": 2}]
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "severity" in result.stdout


def test_declared_variable_difference_is_informational(project: Path) -> None:
    write_record(
        project,
        "comparisons",
        "demo-comparison",
        valid_comparison(
            differences=[{
                "category": "config", "key": "top_k", "run_a_value": 5,
                "run_b_value": 10, "severity": "informational", "declared": True,
            }]
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_diagnostic_suggestions_are_separate_from_validity(project: Path) -> None:
    """agent 的解釋與建議另闢欄位；它永遠不得改變 comparison_valid 或 confounded。"""
    write_record(
        project,
        "comparisons",
        "demo-comparison",
        valid_comparison(
            comparison_valid=False,
            confounded=True,
            controlled_variables_match=False,
            diagnostic_suggestions=["先固定 seed 重跑一次 baseline，成本最低且能分辨是不是取樣雜訊"],
        ),
    )

    result = run_cli("validate", str(project))

    assert result.returncode == 0, result.stdout + result.stderr


def test_removed_other_differences_field_is_rejected(project: Path) -> None:
    """具名差異只有 differences 一份清單；舊欄位不留相容層。"""
    comparison = valid_comparison()
    comparison["comparability"]["other_differences"] = [{"key": "seed"}]
    write_record(project, "comparisons", "demo-comparison", comparison)

    result = run_cli("validate", str(project))

    assert result.returncode == 1
    assert "other_differences" in result.stdout
