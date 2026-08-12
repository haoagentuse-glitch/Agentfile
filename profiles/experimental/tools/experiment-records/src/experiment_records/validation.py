"""驗證實驗 record、project-ref 與不可變生命週期事件序列。"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
import yaml

from experiment_records.project_layout import SUBDIR_TO_SCHEMA, ProjectLayout, record_type_for
from experiment_records.ref_resolver import RefError, RefInvalid, resolve_ref, validate_ref_syntax

Result = tuple[str, str]

_SCHEMA_CACHE: dict[Path, dict[str, Any]] = {}
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


def schema_count() -> int:
    return len(set(SUBDIR_TO_SCHEMA.values()))


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
    for schema_name in dict.fromkeys(SUBDIR_TO_SCHEMA.values()):
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


def _extract_refs(schema: Any, value: Any, path: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if not isinstance(schema, dict):
        return refs
    if schema.get("format") == "project-ref" and isinstance(value, str):
        refs.append((".".join(path), value))
    properties = schema.get("properties")
    if isinstance(properties, dict) and isinstance(value, dict):
        for key, child_schema in properties.items():
            if key in value:
                refs.extend(_extract_refs(child_schema, value[key], (*path, key)))
    items = schema.get("items")
    if isinstance(items, dict) and isinstance(value, list):
        for index, child in enumerate(value):
            refs.extend(_extract_refs(items, child, (*path, str(index))))
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
        Draft202012Validator(schema, format_checker=_PROJECT_FORMAT_CHECKER).iter_errors(instance),
        key=lambda error: list(map(str, error.path)),
    )
    results: list[Result] = []
    for error in errors:
        at = "/".join(str(part) for part in error.path) or "<root>"
        results.append(("錯誤", f"{label}: Schema[{at}]: {error.message}"))
    if errors:
        return results
    results.extend(_validate_lifecycle_event(instance, label, schema, layout))
    for field_label, ref_value in _extract_refs(schema, instance):
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
        Draft202012Validator(schema, format_checker=_PROJECT_FORMAT_CHECKER).iter_errors(instance),
        key=lambda e: list(map(str, e.path)),
    )
    results: list[Result] = []
    if errors:
        for error in errors:
            at = "/".join(str(part) for part in error.path) or "<root>"
            results.append(("錯誤", f"{label}: Schema[{at}]: {error.message}"))
    else:
        results.append(("通過", f"{label}: Schema 有效"))
        if record_type == "lifecycles":
            results.extend(_validate_lifecycle_event(instance, label, schema, layout))
        elif record_type == "definitions":
            results.extend(_validate_contract_configs(instance, label, layout))

    for field_label, ref_value in _extract_refs(schema, instance):
        try:
            resolved = resolve_ref(layout.project_root, ref_value)
        except RefError as e:
            results.append(("錯誤", f"{label}: ref {field_label}={ref_value!r}: {e}"))
        else:
            results.append(("通過", f"{label}: ref {field_label} -> {resolved.relative_to(layout.project_root)} 可解析"))
    return results


def validate_lifecycle_events(paths: list[Path], layout: ProjectLayout) -> list[Result]:
    schema = _load_schema(layout.schemas_dir / SUBDIR_TO_SCHEMA["lifecycles"])
    validator = Draft202012Validator(schema, format_checker=_PROJECT_FORMAT_CHECKER)
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
