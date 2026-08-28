"""compute cascade gate：每一級有預算、升級條件與中止條件，且判定可重現。

門檻凍結在 Contract 的 compute_cascade，不從命令列帶。門檻散在某次呼叫的參數裡，
同一組紀錄就重跑不出同一個判定——那不是確定性，只是剛好那次這樣打。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from helpers import run_cli, valid_comparison, valid_definition, valid_run

CASCADE = [
    {"stage": "preflight", "level": "L0"},
    {
        "stage": "pilot", "level": "L3",
        "budget": {"max_wall_clock_seconds": 600, "max_samples": 200},
        "promotion": {"metric": "recall_at_10", "source": "comparison", "field": "absolute_diff",
                      "comparator": ">=", "threshold": 0.03},
        "abort": {"metric": "latency_ms", "source": "run", "field": "value", "run_scope": "all",
                  "comparator": ">", "threshold": 400,
                  "reason": "延遲超過 guardrail，這條路線終止"},
    },
    {
        "stage": "main", "level": "L5",
        "budget": {"max_cost_usd": 20.0, "max_runs": 4},
        "promotion": {"metric": "recall_at_10", "source": "comparison", "field": "absolute_diff",
                      "comparator": ">=", "threshold": 0.05},
    },
]


def _write(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def bench(tmp_path: Path):
    """一個只放 compute-gate 需要的檔案的工作目錄。"""
    def build(*, cascade: list | None = None, comparison: dict | None = None,
              runs: list[dict] | None = None, current_level: str | None = None) -> dict[str, Path]:
        contract = _write(
            tmp_path / "contract.json",
            valid_definition(compute_cascade=cascade if cascade is not None else CASCADE),
        )
        paths = {"contract": contract, "gate": tmp_path / "gate.json"}
        if current_level is not None:
            _write(paths["gate"], {
                "experiment_id": "demo-exp", "current_level": current_level,
                "history": [], "updated_at": "2026-01-01T00:00:00Z",
            })
        if comparison is not None:
            paths["comparison"] = _write(tmp_path / "comparison.json", comparison)
        for index, run in enumerate(runs or []):
            paths[f"run{index}"] = _write(tmp_path / f"run{index}.json", run)
        return paths

    return build


def _gate(paths: dict[str, Path], level: str, *extra: str) -> subprocess.CompletedProcess[str]:
    command = [
        "compute-gate", str(paths["gate"]),
        "--contract", str(paths["contract"]), "--request-level", level,
        "--decided-at", "2026-01-01T00:00:00Z",
    ]
    if "comparison" in paths:
        command.extend(["--comparison", str(paths["comparison"])])
    for key, path in paths.items():
        if key.startswith("run"):
            command.extend(["--run", str(path)])
    command.extend(extra)
    return run_cli(*command)


def _comparison(absolute_diff: float) -> dict:
    return valid_comparison(metrics={"recall_at_10": {
        "definition_consistent": True, "computed": True,
        "baseline": 0.62, "treatment": 0.62 + absolute_diff,
        "absolute_diff": absolute_diff, "relative_diff": absolute_diff / 0.62,
    }})


def test_second_output_path_is_rejected_without_mutating_gate(bench) -> None:
    paths = bench(current_level="L0", comparison=_comparison(0.06),
                  runs=[valid_run(duration_seconds=400, metrics={"latency_ms": 200})])
    before = paths["gate"].read_text(encoding="utf-8")
    other = paths["gate"].with_name("other-gate.json")

    result = _gate(paths, "L3", "--output", str(other))

    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr
    assert paths["gate"].read_text(encoding="utf-8") == before
    assert not other.exists()

def test_first_level_passes_with_no_metric_gate(bench) -> None:
    paths = bench()

    result = _gate(paths, "L0")

    assert result.returncode == 0, result.stdout + result.stderr
    state = json.loads(paths["gate"].read_text(encoding="utf-8"))
    assert state["current_level"] == "L0"
    assert state["history"][-1]["stage"] == "preflight"


def test_skipping_a_level_is_refused(bench) -> None:
    paths = bench()

    result = _gate(paths, "L5")

    assert result.returncode == 2
    assert "不能跳級" in result.stdout


def test_promotion_threshold_from_the_contract_is_enforced(bench) -> None:
    paths = bench(current_level="L0", comparison=_comparison(0.01),
                  runs=[valid_run(duration_seconds=400, metrics={"latency_ms": 200})])

    result = _gate(paths, "L3")

    assert result.returncode == 1
    assert "升級條件沒過" in result.stdout
    state = json.loads(paths["gate"].read_text(encoding="utf-8"))
    assert state["current_level"] == "L0"
    assert state["history"][-1]["status"] == "failed"


def test_promotion_threshold_met_passes(bench) -> None:
    paths = bench(current_level="L0", comparison=_comparison(0.06),
                  runs=[valid_run(duration_seconds=400, metrics={"latency_ms": 200})])

    result = _gate(paths, "L3")

    assert result.returncode == 0, result.stdout + result.stderr
    state = json.loads(paths["gate"].read_text(encoding="utf-8"))
    assert state["current_level"] == "L3"


def test_abort_rule_terminates_the_route(bench) -> None:
    """中止不是「補證據重來」，是這條路線結束。"""
    paths = bench(current_level="L0", comparison=_comparison(0.06),
                  runs=[valid_run(duration_seconds=400, metrics={"latency_ms": 460})])

    result = _gate(paths, "L3")

    assert result.returncode == 1
    assert "延遲超過 guardrail" in result.stdout
    assert "這條實驗路線視為終止" in result.stdout
    state = json.loads(paths["gate"].read_text(encoding="utf-8"))
    assert state["history"][-1]["status"] == "aborted"


def test_aborted_route_rejects_reentry_without_appending_history(bench) -> None:
    paths = bench(current_level="L0", comparison=_comparison(0.06),
                  runs=[valid_run(duration_seconds=400, metrics={"latency_ms": 460})])
    first = _gate(paths, "L3")
    assert first.returncode == 1
    state_before = paths["gate"].read_text(encoding="utf-8")

    _write(paths["run0"], valid_run(duration_seconds=400, metrics={"latency_ms": 200}))
    retry = _gate(paths, "L3")

    assert retry.returncode == 2
    assert "已中止" in retry.stdout
    assert paths["gate"].read_text(encoding="utf-8") == state_before

def test_abort_is_checked_before_promotion(bench) -> None:
    """升級條件過了也不能蓋過中止條件。"""
    paths = bench(current_level="L0", comparison=_comparison(0.50),
                  runs=[valid_run(duration_seconds=400, metrics={"latency_ms": 900})])

    result = _gate(paths, "L3")

    assert json.loads(paths["gate"].read_text(encoding="utf-8"))["history"][-1]["status"] == "aborted"
    assert result.returncode == 1


def test_budget_overrun_blocks_promotion(bench) -> None:
    paths = bench(current_level="L0", comparison=_comparison(0.06),
                  runs=[valid_run(duration_seconds=900, metrics={"latency_ms": 200})])

    result = _gate(paths, "L3")

    assert result.returncode == 1
    assert "超出 L3 的預算" in result.stdout
    assert "max_wall_clock_seconds=600" in result.stdout


def test_max_runs_budget_is_enforced(bench) -> None:
    runs = [valid_run(run_id=f"r{i}", resource_usage={"cost_usd": 1.0}) for i in range(5)]
    paths = bench(current_level="L3", comparison=_comparison(0.09), runs=runs)

    result = _gate(paths, "L5")

    assert result.returncode == 1
    assert "max_runs=4" in result.stdout


def test_unreadable_metric_fails_rather_than_passes(bench) -> None:
    """取不到值時不得當成通過。「不知道」不等於「符合」。"""
    paths = bench(
        current_level="L0",
        comparison=_comparison(0.06),
        runs=[valid_run(duration_seconds=400, metrics={})],
    )

    result = _gate(paths, "L3")

    assert result.returncode == 1
    assert "無法檢查中止條件" in result.stdout


def test_confounded_comparison_cannot_justify_promotion(bench) -> None:
    confounded = _comparison(0.09)
    confounded["comparison_valid"] = False
    confounded["confounded"] = True
    paths = bench(current_level="L0", comparison=confounded,
                  runs=[valid_run(duration_seconds=400, metrics={"latency_ms": 200})])

    result = _gate(paths, "L3")

    assert result.returncode == 1
    assert "不可引用" in result.stdout


def test_same_input_produces_the_same_decision(bench, tmp_path: Path) -> None:
    """同一組輸入重跑必須得到同一個 status、reason 與 checks。"""
    decisions = []
    for attempt in range(2):
        paths = bench(current_level="L0", comparison=_comparison(0.06),
                      runs=[valid_run(duration_seconds=400, metrics={"latency_ms": 200})])
        paths["gate"] = tmp_path / f"gate-{attempt}.json"
        _write(paths["gate"], {
            "experiment_id": "demo-exp", "current_level": "L0",
            "history": [], "updated_at": "2026-01-01T00:00:00Z",
        })
        _gate(paths, "L3")
        entry = json.loads(paths["gate"].read_text(encoding="utf-8"))["history"][-1]
        decisions.append(entry)

    assert decisions[0] == decisions[1]


def test_decision_records_every_check_it_made(bench) -> None:
    """決定要能回溯到數字，不能只留一句結論。"""
    paths = bench(current_level="L0", comparison=_comparison(0.06),
                  runs=[valid_run(duration_seconds=400, metrics={"latency_ms": 200})])

    _gate(paths, "L3")

    checks = json.loads(paths["gate"].read_text(encoding="utf-8"))["history"][-1]["checks"]
    assert {check["kind"] for check in checks} == {
        "sequence", "evidence", "abort", "budget", "promotion"
    }
    assert all(check["detail"] for check in checks)


def test_contract_without_a_cascade_is_a_usage_error(bench) -> None:
    """門檻必須凍結在 Contract 裡；沒有 cascade 就沒有可重現的判定依據。"""
    paths = bench(cascade=[])

    result = _gate(paths, "L0")

    assert result.returncode == 2
    assert "沒有 compute_cascade" in result.stdout


def test_run_scope_baseline_does_not_apply_abort_to_treatment(bench) -> None:
    cascade = json.loads(json.dumps(CASCADE))
    cascade[1]["abort"]["run_scope"] = "baseline"
    runs = [
        valid_run(run_id="base", baseline_run=None, metrics={"latency_ms": 200}),
        valid_run(run_id="treat", baseline_run="base", metrics={"latency_ms": 900}),
    ]
    paths = bench(current_level="L0", cascade=cascade, comparison=_comparison(0.06), runs=runs)

    result = _gate(paths, "L3")

    assert result.returncode == 0, result.stdout + result.stderr


def test_missing_requested_run_role_fails_closed(bench) -> None:
    cascade = json.loads(json.dumps(CASCADE))
    cascade[1]["abort"]["run_scope"] = "treatment"
    paths = bench(current_level="L0", cascade=cascade, comparison=_comparison(0.06),
                  runs=[valid_run(run_id="base", baseline_run=None, metrics={"latency_ms": 200})])

    result = _gate(paths, "L3")

    assert result.returncode == 1
    assert "treatment" in result.stdout


def test_ineligible_run_stage_cannot_pass_gate(bench) -> None:
    paths = bench(current_level="L0", comparison=_comparison(0.06), runs=[
        valid_run(stage="diagnostic", duration_seconds=400, metrics={"latency_ms": 200})
    ])

    result = _gate(paths, "L3")

    assert result.returncode == 1
    state = json.loads(paths["gate"].read_text(encoding="utf-8"))
    assert state["history"][-1]["evidence_eligible"] is False


def test_history_run_ids_are_derived_and_run_ids_option_is_removed(bench) -> None:
    paths = bench(current_level="L0", comparison=_comparison(0.06), runs=[
        valid_run(run_id="base", baseline_run=None, duration_seconds=400, metrics={"latency_ms": 200})
    ])

    rejected = _gate(paths, "L3", "--run-ids", "forged")
    assert rejected.returncode == 2
    assert not paths["gate"].exists() or json.loads(paths["gate"].read_text())["history"] == []

    passed = _gate(paths, "L3")
    assert passed.returncode == 0
    state = json.loads(paths["gate"].read_text(encoding="utf-8"))
    assert state["history"][-1]["run_ids"] == ["base"]


def test_level_absent_from_the_cascade_is_a_usage_error(bench) -> None:
    paths = bench(cascade=[{"stage": "preflight", "level": "L0"}], current_level="L0")

    result = _gate(paths, "L1")

    assert result.returncode == 2
