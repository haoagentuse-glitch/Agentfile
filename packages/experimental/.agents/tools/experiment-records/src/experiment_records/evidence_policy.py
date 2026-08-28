"""Contract-driven evidence eligibility checks shared by record producers.

The evaluator is deliberately fail closed: evidence is eligible only when the
policy is present, every run is in an allowed stage, and baseline/treatment
operation 所需的 roles can be derived uniquely from run lineage.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _resolve_roles(runs: Sequence[Mapping[str, Any]]) -> dict[str, str] | None:
    if not 1 <= len(runs) <= 2:
        return None
    roles: dict[str, str] = {}
    for run in runs:
        run_id = run.get("run_id")
        if not isinstance(run_id, str) or not run_id or "baseline_run" not in run:
            return None
        role = "baseline" if run["baseline_run"] is None else "treatment"
        if role in roles:
            return None
        roles[role] = run_id
    if len(runs) == 1:
        return roles
    baseline = next(run for run in runs if run.get("baseline_run") is None)
    treatment = next(run for run in runs if run.get("baseline_run") is not None)
    if treatment.get("baseline_run") != baseline.get("run_id"):
        return None
    return roles


def evaluate_evidence_policy(
    contract: Mapping[str, Any],
    runs: Sequence[Mapping[str, Any]],
    required_roles: frozenset[str] = frozenset({"baseline", "treatment"}),
) -> dict[str, Any]:
    """Return a serializable ``eligible`` decision, reasons, and resolved roles."""
    policy = contract.get("evidence_policy")
    stages = policy.get("eligible_run_stages") if isinstance(policy, Mapping) else None
    if (
        not isinstance(stages, list)
        or not stages
        or any(not isinstance(stage, str) or not stage for stage in stages)
    ):
        return {
            "eligible": False,
            "reasons": ["Contract 缺少有效的 evidence_policy.eligible_run_stages"],
            "roles": None,
        }

    roles = _resolve_roles(runs)
    reasons: list[str] = []
    if not runs:
        reasons.append("沒有提供任何 run，無法判定 evidence eligibility")
    expected_experiment_id = contract.get("experiment_id")
    run_ids = [run.get("run_id") for run in runs]
    valid_run_ids = [run_id for run_id in run_ids if isinstance(run_id, str) and run_id]
    if len(valid_run_ids) != len(run_ids):
        reasons.append("run_id 缺少或不是非空字串")
    if len(valid_run_ids) != len(set(valid_run_ids)):
        reasons.append("run_id 重複，無法唯一識別 evidence")
    allowed = tuple(stages)
    for run in runs:
        if run.get("experiment_id") != expected_experiment_id:
            reasons.append(
                f"run {run.get('run_id', '?')!r} 不屬於目標 experiment "
                f"{expected_experiment_id!r}"
            )
        if run.get("status") != "completed":
            run_id = run.get("run_id", "?")
            reasons.append(f"run {run_id!r} status 不是 completed")
        stage = run.get("stage")
        if stage not in stages:
            reasons.append(
                f"run {run.get('run_id', '?')!r} stage {stage!r} "
                f"不在 evidence_policy.eligible_run_stages {allowed!r}"
            )
    if required_roles:
        if roles is None:
            role_names = " 與 ".join(sorted(required_roles))
            reasons.append(
                f"無法由 baseline_run lineage 唯一解析 {role_names} 角色"
            )
        else:
            for role in sorted(required_roles):
                if role not in roles:
                    reasons.append(f"缺少可解析的 {role} run")

    return {"eligible": not reasons, "reasons": reasons, "roles": roles}
