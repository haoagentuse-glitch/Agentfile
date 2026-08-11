"""對單一 record 檔案跑完整 JSON Schema Draft 2020-12 驗證，再核對它引用的
Schema `format: project-ref` 欄位是否為合法、可解析的 project-root-relative 路徑。

用 `jsonschema` 這個成熟函式庫做完整驗證（含 additionalProperties、pattern、
format、allOf/if-then），不是像舊版 experiment_lint.py 那樣只遞迴檢查
required/enum——那支是刻意的簡化版，這裡是這個新套件對外承諾的「完整驗證」。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from experiment_records.project_layout import SUBDIR_TO_SCHEMA, ProjectLayout, record_type_for
from experiment_records.ref_resolver import (
    RefError,
    RefInvalid,
    resolve_ref,
    validate_ref_syntax,
)

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


def validate_schemas(layout: ProjectLayout) -> list[Result]:
    results: list[Result] = []
    for schema_name in dict.fromkeys(SUBDIR_TO_SCHEMA.values()):
        schema_path = layout.schemas_dir / schema_name
        try:
            _load_schema(schema_path)
        except (json.JSONDecodeError, OSError, SchemaError, TypeError) as e:
            detail = e.message if isinstance(e, SchemaError) else str(e)
            results.append(
                ("錯誤", f"schemas/{schema_name}: Schema 本身無效：{detail}")
            )
        else:
            results.append(("通過", f"schemas/{schema_name}: Schema 有效"))
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
                child_path = (*path, key)
                refs.extend(
                    _extract_refs(child_schema, value[key], child_path)
                )

    items = schema.get("items")
    if isinstance(items, dict) and isinstance(value, list):
        for index, child in enumerate(value):
            refs.extend(_extract_refs(items, child, (*path, str(index))))
    return refs


def validate_record(path: Path, layout: ProjectLayout) -> list[Result]:
    label = _label(path, layout)
    results: list[Result] = []

    try:
        with path.open("r", encoding="utf-8") as f:
            instance = json.load(f)
    except json.JSONDecodeError as e:
        results.append(("錯誤", f"{label}: 不是合法 JSON：{e}"))
        return results

    record_type = record_type_for(path)
    if record_type is None:
        results.append(
            ("錯誤", f"{label}: 無法辨識 record 類型——父目錄 {path.parent.name!r} 不在已知清單中")
        )
        return results

    if not isinstance(instance, dict):
        results.append(("錯誤", f"{label}: record 最外層必須是 JSON object"))
        return results

    schema_path = layout.schemas_dir / SUBDIR_TO_SCHEMA[record_type]
    try:
        schema = _load_schema(schema_path)
    except (json.JSONDecodeError, OSError, SchemaError, TypeError) as e:
        detail = e.message if isinstance(e, SchemaError) else str(e)
        results.append(
            ("錯誤", f"{label}: Schema {schema_path.name} 本身無效：{detail}")
        )
        return results
    validator = Draft202012Validator(schema, format_checker=_PROJECT_FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(map(str, e.path)))

    if errors:
        for e in errors:
            at = "/".join(str(p) for p in e.path) or "<root>"
            results.append(("錯誤", f"{label}: Schema[{at}]: {e.message}"))
    else:
        results.append(("通過", f"{label}: Schema 有效"))

    for field_label, ref_value in _extract_refs(schema, instance):
        try:
            resolved = resolve_ref(layout.project_root, ref_value)
        except RefError as e:
            results.append(("錯誤", f"{label}: ref {field_label}={ref_value!r}: {e}"))
        else:
            results.append(("通過", f"{label}: ref {field_label} -> {resolved.relative_to(layout.project_root)} 可解析"))

    return results
