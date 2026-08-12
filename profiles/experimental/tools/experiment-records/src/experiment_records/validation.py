"""驗證實驗 record、project-ref 與不可變生命週期事件序列。"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
import yaml

from experiment_records.project_layout import (
    SUBDIR_TO_SCHEMA,
    ProjectLayout,
    all_schema_names,
    record_type_for,
)
from experiment_records.prompts import hash_file, prompt_path
from experiment_records.ref_resolver import RefError, RefInvalid, resolve_ref, validate_ref_syntax

Result = tuple[str, str]

_SCHEMA_CACHE: dict[Path, dict[str, Any]] = {}
_REGISTRY_CACHE: dict[Path, Registry] = {}
_PROJECT_FORMAT_CHECKER = FormatChecker()


@_PROJECT_FORMAT_CHECKER.checks("project-ref", raises=RefInvalid)
def _is_project_ref(value: object) -> bool:
    if not isinstance(value, str):
        return True
    validate_ref_syntax(value)
    return True


def _load_schema(schema_path: Path) -> dict[str, Any]:
    cached = _SCHEMA_CACHE.get(schema_path)
    if cached is not None:
        return cached
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    _SCHEMA_CACHE[schema_path] = schema
    return schema


def _registry(layout: ProjectLayout) -> Registry:
    """讓 schema 之間的 $ref（例如 provenance.schema.json#/$defs/producer）可解析。

    只註冊本 project schemas_dir 底下的檔案，不做網路取回——schema 是專案內的權威來源，
    驗證結果不得依賴外部可用性。
    """
    cached = _REGISTRY_CACHE.get(layout.schemas_dir)
    if cached is not None:
        return cached
    resources = []
    for schema_name in all_schema_names():
        try:
            schema = _load_schema(layout.schemas_dir / schema_name)
        except (json.JSONDecodeError, OSError, SchemaError, TypeError):
            continue  # schema 本身無效由 validate_schemas 報告，這裡不重複報
        resources.append((schema_name, Resource.from_contents(schema, default_specification=DRAFT202012)))
    registry = Registry().with_resources(resources)
    _REGISTRY_CACHE[layout.schemas_dir] = registry
    return registry


def _validator(schema: dict[str, Any], layout: ProjectLayout) -> Draft202012Validator:
    return Draft202012Validator(
        schema, registry=_registry(layout), format_checker=_PROJECT_FORMAT_CHECKER
    )


def schema_count() -> int:
    return len(all_schema_names())


def _validate_lifecycle_schema(schema: dict[str, Any]) -> list[Result]:
    states = set(schema.get("$defs", {}).get("lifecycleState", {}).get("enum", []))
    initial_state = schema.get("x-initial-state")
    transitions = schema.get("x-allowed-transitions")
    required_evidence = schema.get("x-required-evidence-subdirs", {})
    new_evidence_states = schema.get("x-requires-new-evidence", [])

    if not states or not isinstance(transitions, dict):
        return [("錯誤", "schemas/lifecycle-state.schema.json: 缺少 lifecycle states 或轉移表")]
    if initial_state not in states:
        return [("錯誤", "schemas/lifecycle-state.schema.json: x-initial-state 不在 state enum")]
    if set(transitions) != states:
        return [("錯誤", "schemas/lifecycle-state.schema.json: 轉移表必須為每個 state 定義出口")]
    if any(
        not isinstance(destinations, list)
        or any(not isinstance(destination, str) for destination in destinations)
        for destinations in transitions.values()
    ):
        return [("錯誤", "schemas/lifecycle-state.schema.json: 每個轉移出口必須是 state 字串陣列")]

    unknown_destinations = {
        destination
        for destinations in transitions.values()
        for destination in destinations
        if destination not in states
    }
    if unknown_destinations:
        return [("錯誤", "schemas/lifecycle-state.schema.json: 轉移表含未知 state：" + ", ".join(sorted(unknown_destinations)))]
    if (
        not isinstance(required_evidence, dict)
        or any(state not in states or not isinstance(subdir, str) for state, subdir in required_evidence.items())
    ):
        return [("錯誤", "schemas/lifecycle-state.schema.json: x-required-evidence-subdirs 無效")]
    if (
        not isinstance(new_evidence_states, list)
        or any(not isinstance(state, str) or state not in states for state in new_evidence_states)
    ):
        return [("錯誤", "schemas/lifecycle-state.schema.json: x-requires-new-evidence 無效")]
    return [("通過", "schemas/lifecycle-state.schema.json: 生命週期轉移表有效")]


def validate_schemas(layout: ProjectLayout) -> list[Result]:
    results: list[Result] = []
    for schema_name in all_schema_names():
        schema_path = layout.schemas_dir / schema_name
        try:
            schema = _load_schema(schema_path)
        except (json.JSONDecodeError, OSError, SchemaError, TypeError) as e:
            detail = e.message if isinstance(e, SchemaError) else str(e)
            results.append(("錯誤", f"schemas/{schema_name}: Schema 本身無效：{detail}"))
        else:
            results.append(("通過", f"schemas/{schema_name}: Schema 有效"))
            if schema_name == "lifecycle-state.schema.json":
                results.extend(_validate_lifecycle_schema(schema))
    return results


def _label(path: Path, layout: ProjectLayout) -> str:
    try:
        return str(path.relative_to(layout.project_root))
    except ValueError:
        return str(path)


def _deref(
    schema: dict[str, Any], document: dict[str, Any], layout: ProjectLayout
) -> tuple[dict[str, Any], dict[str, Any]]:
    """跟隨 $ref 直到拿到實際 subschema，回傳 (subschema, 它所屬的 document)。

    document 要一起回傳，因為跨檔 $ref 之後，後續的同檔 `#/$defs/...` 必須以新檔為基準。
    解析不到就回空 schema——schema 本身的錯誤由 validate_schemas 負責報告，這裡只做 ref 擷取。
    """
    seen: set[str] = set()
    while isinstance(schema, dict) and isinstance(schema.get("$ref"), str):
        ref: str = schema["$ref"]
        if ref in seen:
            return {}, document
        seen.add(ref)
        document_name, _, pointer = ref.partition("#")
        if document_name:
            try:
                document = _load_schema(layout.schemas_dir / document_name)
            except (json.JSONDecodeError, OSError, SchemaError, TypeError):
                return {}, document
        target: Any = document
        for part in pointer.split("/"):
            if not part:
                continue
            key = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(target, dict) or key not in target:
                return {}, document
            target = target[key]
        schema = target if isinstance(target, dict) else {}
    return schema, document


def _extract_refs(
    schema: Any,
    value: Any,
    layout: ProjectLayout,
    document: dict[str, Any] | None = None,
    path: tuple[str, ...] = (),
) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if not isinstance(schema, dict):
        return refs
    if document is None:
        document = schema
    schema, document = _deref(schema, document, layout)
    if schema.get("format") == "project-ref" and isinstance(value, str):
        refs.append((".".join(path), value))
    properties = schema.get("properties")
    if isinstance(properties, dict) and isinstance(value, dict):
        for key, child_schema in properties.items():
            if key in value:
                refs.extend(_extract_refs(child_schema, value[key], layout, document, (*path, key)))
    items = schema.get("items")
    if isinstance(items, dict) and isinstance(value, list):
        for index, child in enumerate(value):
            refs.extend(_extract_refs(items, child, layout, document, (*path, str(index))))
    return refs


def _evidence_experiment_id(path: Path, subdir: str, layout: ProjectLayout) -> str | None:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(record, dict):
        return None
    if subdir == "comparisons":
        experiment_id = record.get("experiment_id")
        return experiment_id if isinstance(experiment_id, str) else None
    if subdir == "audits":
        claim_id = record.get("claim_id")
        if not isinstance(claim_id, str):
            return None
        claims_dir = layout.records_root / "claims"
        for claim_path in sorted(claims_dir.glob("*.json")):
            try:
                claim = json.loads(claim_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(claim, dict) and claim.get("claim_id") == claim_id:
                experiment_id = claim.get("experiment_id")
                if isinstance(experiment_id, str):
                    return experiment_id
    return None


def _validate_lifecycle_event(
    instance: dict[str, Any], label: str, schema: dict[str, Any], layout: ProjectLayout
) -> list[Result]:
    initial_state: str = schema["x-initial-state"]
    transitions: dict[str, list[str]] = schema["x-allowed-transitions"]
    from_state = instance["from_state"]
    to_state = instance["to_state"]
    allowed = [initial_state] if from_state is None else transitions[from_state]
    if to_state not in allowed:
        source = "null" if from_state is None else from_state
        return [("錯誤", f"{label}: 非法生命週期轉移：{source} -> {to_state}")]

    required_subdir = schema.get("x-required-evidence-subdirs", {}).get(to_state)
    if not required_subdir:
        return []
    prefix = f"records/experiments/{required_subdir}/"
    gate_refs = [ref for ref in instance["evidence_refs"] if ref.startswith(prefix)]
    if not gate_refs:
        return [("錯誤", f"{label}: 進入 {to_state} 必須引用 {required_subdir}/ record")]

    results: list[Result] = []
    for ref in gate_refs:
        try:
            resolved = resolve_ref(layout.project_root, ref)
        except RefError:
            continue
        evidence_experiment_id = _evidence_experiment_id(resolved, required_subdir, layout)
        if evidence_experiment_id != instance["experiment_id"]:
            results.append(("錯誤", f"{label}: evidence {ref!r} 不屬於 experiment {instance['experiment_id']!r}"))
    return results


_BUDGET_CHECKS: tuple[tuple[str, str, str], ...] = (
    ("max_wall_clock_seconds", "duration_seconds", "牆鐘秒數"),
    ("max_samples", "resource_usage.samples", "樣本數"),
    ("max_cost_usd", "resource_usage.cost_usd", "花費"),
    ("max_tokens", "resource_usage.tokens_out", "輸出 token 數"),
)


def _run_usage(instance: dict[str, Any], field: str) -> float | None:
    """取 budget 對照用的實際用量；field 可以是頂層欄位或 resource_usage 底下的欄位。"""
    head, _, tail = field.partition(".")
    value = instance.get(head)
    if tail:
        value = value.get(tail) if isinstance(value, dict) else None
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _validate_run(instance: dict[str, Any], label: str) -> list[Result]:
    """單筆 run 的確定性檢查——不需要看其他 run 就能判定的部分。"""
    results: list[Result] = []

    # 相對「哪一次 run」再跑一次，必須說得出是哪一次。
    if instance.get("attempt_kind") not in (None, "initial") and not instance.get("parent_run_id"):
        results.append(("錯誤", f"{label}: attempt_kind={instance['attempt_kind']!r} 必須指定 parent_run_id"))
    if instance.get("stage") == "replication" and not instance.get("parent_run_id"):
        results.append(("錯誤", f"{label}: stage=replication 必須指定 parent_run_id"))

    # 超出預算卻沒有中止原因，代表預算不是真的預算。
    budget = instance.get("budget_limit")
    if isinstance(budget, dict) and not instance.get("abort_reason"):
        for limit_field, usage_field, noun in _BUDGET_CHECKS:
            limit = budget.get(limit_field)
            usage = _run_usage(instance, usage_field)
            if isinstance(limit, (int, float)) and usage is not None and usage > limit:
                results.append((
                    "錯誤",
                    f"{label}: {noun} {usage} 超過 budget_limit.{limit_field}={limit}，但沒有 abort_reason",
                ))

    # 完成的 run 若既沒固定種子、也沒列出不確定性來源，就無法判斷它能不能重現。
    if (
        instance.get("status") == "completed"
        and instance.get("seed") is None
        and not instance.get("nondeterminism_sources")
    ):
        results.append(("警告", f"{label}: 未宣告 seed，也未列出 nondeterminism_sources"))

    return results


def _validate_producer_prompt(instance: dict[str, Any], label: str, layout: ProjectLayout) -> list[Result]:
    """producer 引用本專案管理的 prompt role 時，prompt_hash 必須對得上實際檔案內容。

    prompt 改了而 hash 沒改，就是把 prompt 漂移藏起來——同名 prompt 產生的兩份紀錄
    會被誤認為可比較。專案自有的 prompt（prompts/ 底下找不到）略過，不能驗證的東西
    不假裝驗證過。
    """
    producer = instance.get("producer")
    if not isinstance(producer, dict):
        return []
    prompt_id = producer.get("prompt_id")
    if not isinstance(prompt_id, str):
        return []
    path = prompt_path(layout, prompt_id)
    if path is None:
        return []

    expected = hash_file(path)
    actual = producer.get("prompt_hash")
    if actual is None:
        return [("警告", f"{label}: prompt_id={prompt_id!r} 由本專案管理，但沒有記錄 prompt_hash")]
    if actual != expected:
        return [(
            "錯誤",
            f"{label}: prompt_hash 與 prompts/{prompt_id}.md 實際內容不符；"
            f"預期 {expected}，收到 {actual}",
        )]
    return []


def _same_producer(a: Any, b: Any) -> bool:
    """兩份紀錄是不是同一個產出者做的。

    比對 name 與 prompt_id：同一個 agent 用同一版 prompt 自寫自審，就不是獨立審核。
    兩邊都沒有 producer 時無從判斷，回 False——不能因為欄位空著就推定有問題。
    """
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    return (a.get("name"), a.get("prompt_id")) == (b.get("name"), b.get("prompt_id"))


def _validate_audit(instance: dict[str, Any], label: str) -> list[Result]:
    """單筆 audit 的確定性檢查：結論不得比它自己記錄的檢查結果更強。"""
    results: list[Result] = []
    final_verdict = instance.get("final_verdict")
    mechanical_pass = instance.get("mechanical", {}).get("mechanical_pass")

    if mechanical_pass is False and final_verdict in ("fully_supported", "partially_supported"):
        results.append((
            "錯誤",
            f"{label}: mechanical_pass 為 false，final_verdict 不得是 {final_verdict}",
        ))

    independence = instance.get("review_independence")
    if isinstance(independence, dict):
        if independence.get("independent") is False and final_verdict == "fully_supported":
            results.append((
                "錯誤",
                f"{label}: 審核者不獨立於產出者，final_verdict 不得是 fully_supported",
            ))
        if independence.get("reviewer_kind") == "same_context" and independence.get("independent") is True:
            results.append(("錯誤", f"{label}: reviewer_kind=same_context 不可能是獨立審核"))

    novelty = instance.get("novelty")
    if isinstance(novelty, dict):
        if novelty.get("status") == "novel_confirmed" and not novelty.get("source_refs"):
            results.append((
                "錯誤",
                f"{label}: novelty.status=novel_confirmed 但沒有任何 source_refs；未查證只能標 unverified",
            ))

    return results


def validate_claim_audit_chain(paths: list[Path], layout: ProjectLayout) -> list[Result]:
    """跨檔檢查 claim 與 audit 的關係。

    兩件事只有把兩份紀錄放在一起才判得出來：claim 標 supported 時是否真的有稽核撐著，
    以及稽核者是不是就是寫這個 claim 的同一個 agent 與同一版 prompt。
    """
    claims: dict[str, tuple[str, dict[str, Any]]] = {}
    audits: dict[str, tuple[str, dict[str, Any]]] = {}
    for path in paths:
        record_type = record_type_for(path)
        if record_type not in ("claims", "audits"):
            continue
        try:
            instance = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(instance, dict):
            continue
        claim_id = instance.get("claim_id")
        if not isinstance(claim_id, str):
            continue
        (claims if record_type == "claims" else audits)[claim_id] = (_label(path, layout), instance)

    results: list[Result] = []
    for claim_id, (label, claim) in sorted(claims.items()):
        audit_entry = audits.get(claim_id)

        if claim.get("status") == "supported":
            if audit_entry is None:
                results.append(("錯誤", f"{label}: status=supported 但沒有對應的 claim-audit-result"))
            elif audit_entry[1].get("final_verdict") not in ("fully_supported", "partially_supported"):
                results.append((
                    "錯誤",
                    f"{label}: status=supported 但稽核結論是 {audit_entry[1].get('final_verdict')!r}",
                ))

        if audit_entry is None:
            continue
        audit_label, audit = audit_entry
        if _same_producer(claim.get("producer"), audit.get("producer")):
            independence = audit.get("review_independence")
            if not isinstance(independence, dict) or independence.get("independent") is not False:
                results.append((
                    "錯誤",
                    f"{audit_label}: 稽核者與 claim 產出者相同（同一 name 與 prompt_id），"
                    "review_independence.independent 必須是 false",
                ))

    for claim_id, (label, _audit) in sorted(audits.items()):
        if claim_id not in claims:
            results.append(("錯誤", f"{label}: 稽核的 claim_id {claim_id!r} 不存在"))
    return results


def validate_run_lineage(paths: list[Path], layout: ProjectLayout) -> list[Result]:
    """跨檔 lineage 檢查：parent_run_id 必須指到存在的 run，且不得成環。

    指不到的 parent 會讓 replication 與 retry 的來源無法回溯；成環則讓 lineage 無法收斂。
    兩者都是結構問題，不是語意判斷。
    """
    runs: dict[str, str] = {}
    parents: dict[str, str] = {}
    for path in paths:
        if record_type_for(path) != "runs":
            continue
        try:
            instance = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        run_id = instance.get("run_id") if isinstance(instance, dict) else None
        if not isinstance(run_id, str):
            continue
        runs[run_id] = _label(path, layout)
        parent = instance.get("parent_run_id")
        if isinstance(parent, str):
            parents[run_id] = parent

    results: list[Result] = []
    for run_id, parent in sorted(parents.items()):
        label = runs[run_id]
        if parent == run_id:
            results.append(("錯誤", f"{label}: parent_run_id 指向自己"))
            continue
        if parent not in runs:
            results.append(("錯誤", f"{label}: parent_run_id {parent!r} 指向不存在的 run"))
            continue
        seen = {run_id}
        cursor = parent
        while cursor in parents:
            if cursor in seen:
                results.append(("錯誤", f"{label}: parent_run_id 形成循環 lineage"))
                break
            seen.add(cursor)
            cursor = parents[cursor]
    return results


def _validate_derivation(instance: dict[str, Any], label: str) -> list[Result]:
    """Research Question Certificate 的確定性硬檢查。

    只檢查可由結構本身判定的事：ID 唯一、引用可解、宣告與證據一致。
    「這個機制講得對不對」是語意判斷，不在這裡做，也不得由這裡放行。
    """
    derivation = instance.get("derivation")
    if not isinstance(derivation, dict):
        return []

    results: list[Result] = []

    primitive_ids = [p["id"] for p in derivation.get("primitives", []) if isinstance(p, dict) and "id" in p]
    duplicate_primitives = sorted({i for i in primitive_ids if primitive_ids.count(i) > 1})
    if duplicate_primitives:
        results.append(("錯誤", f"{label}: derivation.primitives ID 重複：{', '.join(duplicate_primitives)}"))

    assumption_ids = [a["id"] for a in derivation.get("assumptions", []) if isinstance(a, dict) and "id" in a]
    duplicate_assumptions = sorted({i for i in assumption_ids if assumption_ids.count(i) > 1})
    if duplicate_assumptions:
        results.append(("錯誤", f"{label}: derivation.assumptions ID 重複：{', '.join(duplicate_assumptions)}"))

    known_assumptions = set(assumption_ids)
    for index, rule in enumerate(derivation.get("failure_update", [])):
        if not isinstance(rule, dict):
            continue
        target = rule.get("update_assumption_id")
        if target not in known_assumptions:
            results.append((
                "錯誤",
                f"{label}: derivation.failure_update[{index}] 指向不存在的 assumption {target!r}",
            ))

    # 沒有保存下來的來源就不得宣告新穎性——模型憑記憶判斷新穎性會系統性高估。
    if derivation.get("novelty_status") != "unverified" and not derivation.get("source_refs"):
        results.append((
            "錯誤",
            f"{label}: novelty_status={derivation.get('novelty_status')!r} 但 source_refs 為空；未查證只能標 unverified",
        ))

    # 機制模型必須提到實際被操弄的變因，否則這個機制敘述跟這個實驗無關。
    treatment_variable = instance.get("treatment", {}).get("variable")
    variables = derivation.get("mechanism_model", {}).get("variables", [])
    if isinstance(treatment_variable, str) and isinstance(variables, list) and treatment_variable not in variables:
        results.append((
            "錯誤",
            f"{label}: mechanism_model.variables 未包含 treatment.variable {treatment_variable!r}",
        ))

    return results


def _validate_contract_configs(instance: dict[str, Any], label: str, layout: ProjectLayout) -> list[Result]:
    baseline_ref = instance.get("baseline", {}).get("config_ref")
    treatment_ref = instance.get("treatment", {}).get("config_ref")
    if not isinstance(baseline_ref, str) or not isinstance(treatment_ref, str):
        return []
    try:
        baseline_path = resolve_ref(layout.project_root, baseline_ref)
        treatment_path = resolve_ref(layout.project_root, treatment_ref)
    except RefError:
        return []
    try:
        baseline = yaml.safe_load(baseline_path.read_text(encoding="utf-8"))
        treatment = yaml.safe_load(treatment_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        return [("錯誤", f"{label}: baseline/treatment config 無法解析：{error}")]
    if not isinstance(baseline, dict) or not isinstance(treatment, dict):
        return [("錯誤", f"{label}: baseline/treatment config 最外層必須是 object")]

    results: list[Result] = []
    controlled = set(instance.get("controlled_variables", []))
    treatment_variable = instance.get("treatment", {}).get("variable")
    for key in sorted(set(baseline) | set(treatment)):
        baseline_value = baseline.get(key, "<absent>")
        treatment_value = treatment.get(key, "<absent>")
        if baseline_value == treatment_value:
            continue
        if key in controlled:
            results.append(("錯誤", f"{label}: controlled_variable {key!r} 實際不同；實驗不可識別"))
        elif key != treatment_variable:
            results.append(("錯誤", f"{label}: 未宣告的設定差異 {key!r}；實驗不可識別"))
    if "seed" not in controlled and "seed" not in str(treatment_variable or ""):
        results.append(("警告", f"{label}: controlled_variables 未宣告 random seed"))
    return results

def validate_lifecycle_candidate(
    instance: dict[str, Any], label: str, layout: ProjectLayout
) -> list[Result]:
    schema = _load_schema(layout.schemas_dir / SUBDIR_TO_SCHEMA["lifecycles"])
    errors = sorted(
        _validator(schema, layout).iter_errors(instance),
        key=lambda error: list(map(str, error.path)),
    )
    results: list[Result] = []
    for error in errors:
        at = "/".join(str(part) for part in error.path) or "<root>"
        results.append(("錯誤", f"{label}: Schema[{at}]: {error.message}"))
    if errors:
        return results
    results.extend(_validate_lifecycle_event(instance, label, schema, layout))
    for field_label, ref_value in _extract_refs(schema, instance, layout):
        try:
            resolve_ref(layout.project_root, ref_value)
        except RefError as error:
            results.append(("錯誤", f"{label}: ref {field_label}={ref_value!r}: {error}"))
    return results

def validate_lifecycle_history_candidate(
    existing_events: list[dict[str, Any]], candidate: dict[str, Any], label: str, layout: ProjectLayout
) -> list[Result]:
    schema = _load_schema(layout.schemas_dir / SUBDIR_TO_SCHEMA["lifecycles"])
    if candidate["to_state"] not in schema.get("x-requires-new-evidence", []):
        return []
    prior_refs = {
        ref
        for event in existing_events
        for ref in event.get("evidence_refs", [])
        if isinstance(ref, str)
    }
    if set(candidate["evidence_refs"]) - prior_refs:
        return []
    return [("錯誤", f"{label}: 進入 {candidate['to_state']} 必須引用先前未使用的新證據")]

def validate_record(path: Path, layout: ProjectLayout) -> list[Result]:
    label = _label(path, layout)
    try:
        with path.open("r", encoding="utf-8") as f:
            instance = json.load(f)
    except json.JSONDecodeError as e:
        return [("錯誤", f"{label}: 不是合法 JSON：{e}")]

    record_type = record_type_for(path)
    if record_type is None:
        return [("錯誤", f"{label}: 無法辨識 record 類型——父目錄 {path.parent.name!r} 不在已知清單中")]
    if not isinstance(instance, dict):
        return [("錯誤", f"{label}: record 最外層必須是 JSON object")]

    schema_path = layout.schemas_dir / SUBDIR_TO_SCHEMA[record_type]
    try:
        schema = _load_schema(schema_path)
    except (json.JSONDecodeError, OSError, SchemaError, TypeError) as e:
        detail = e.message if isinstance(e, SchemaError) else str(e)
        return [("錯誤", f"{label}: Schema {schema_path.name} 本身無效：{detail}")]

    errors = sorted(
        _validator(schema, layout).iter_errors(instance),
        key=lambda e: list(map(str, e.path)),
    )
    results: list[Result] = []
    if errors:
        for error in errors:
            at = "/".join(str(part) for part in error.path) or "<root>"
            results.append(("錯誤", f"{label}: Schema[{at}]: {error.message}"))
    else:
        results.append(("通過", f"{label}: Schema 有效"))
        results.extend(_validate_producer_prompt(instance, label, layout))
        if record_type == "lifecycles":
            results.extend(_validate_lifecycle_event(instance, label, schema, layout))
        elif record_type == "definitions":
            results.extend(_validate_derivation(instance, label))
            results.extend(_validate_contract_configs(instance, label, layout))
        elif record_type == "runs":
            results.extend(_validate_run(instance, label))
        elif record_type == "audits":
            results.extend(_validate_audit(instance, label))

    for field_label, ref_value in _extract_refs(schema, instance, layout):
        try:
            resolved = resolve_ref(layout.project_root, ref_value)
        except RefError as e:
            results.append(("錯誤", f"{label}: ref {field_label}={ref_value!r}: {e}"))
        else:
            results.append(("通過", f"{label}: ref {field_label} -> {resolved.relative_to(layout.project_root)} 可解析"))
    return results


def validate_lifecycle_events(paths: list[Path], layout: ProjectLayout) -> list[Result]:
    schema = _load_schema(layout.schemas_dir / SUBDIR_TO_SCHEMA["lifecycles"])
    validator = _validator(schema, layout)
    grouped: dict[str, list[tuple[Path, dict[str, Any]]]] = defaultdict(list)

    for path in paths:
        if record_type_for(path) != "lifecycles":
            continue
        try:
            instance = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(instance, dict) and not list(validator.iter_errors(instance)):
            grouped[instance["experiment_id"]].append((path, instance))

    results: list[Result] = []
    for experiment_id, events in sorted(grouped.items()):
        events.sort(key=lambda item: item[1]["sequence"])
        previous_state: str | None = None
        prior_refs: set[str] = set()
        for expected_sequence, (path, event) in enumerate(events, start=1):
            label = _label(path, layout)
            if event["sequence"] != expected_sequence:
                results.append(("錯誤", f"{label}: sequence 必須連續；預期 {expected_sequence}，收到 {event['sequence']}"))
                break
            if event["from_state"] != previous_state:
                results.append(("錯誤", f"{label}: 事件不連續；from_state={event['from_state']!r}，前一狀態是 {previous_state!r}"))
                break
            refs = set(event["evidence_refs"])
            if event["to_state"] in schema.get("x-requires-new-evidence", []) and not (refs - prior_refs):
                results.append(("錯誤", f"{label}: 進入 {event['to_state']} 必須引用先前未使用的新證據"))
                break
            prior_refs.update(refs)
            previous_state = event["to_state"]
        else:
            results.append(("通過", f"lifecycles/{experiment_id}: 生命週期轉移合法；事件序列完整；目前狀態={previous_state}"))
    return results
