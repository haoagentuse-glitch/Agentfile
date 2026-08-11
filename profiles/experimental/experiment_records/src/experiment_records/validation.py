"""對單一 record 檔案跑完整 JSON Schema Draft 2020-12 驗證，再核對它引用的
`*_ref` 欄位是否為合法、可解析的 project-root-relative 路徑。

用 `jsonschema` 這個成熟函式庫做完整驗證（含 additionalProperties、pattern、
format、allOf/if-then），不是像舊版 experiment_lint.py 那樣只遞迴檢查
required/enum——那支是刻意的簡化版，這裡是這個新套件對外承諾的「完整驗證」。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from experiment_records.project_layout import SUBDIR_TO_SCHEMA, ProjectLayout, record_type_for
from experiment_records.ref_resolver import RefError, resolve_ref

Result = tuple[str, str]

_SCHEMA_CACHE: dict[Path, dict[str, Any]] = {}


def _load_schema(schema_path: Path) -> dict[str, Any]:
    cached = _SCHEMA_CACHE.get(schema_path)
    if cached is not None:
        return cached
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    _SCHEMA_CACHE[schema_path] = schema
    return schema


def _label(path: Path, layout: ProjectLayout) -> str:
    try:
        return str(path.relative_to(layout.project_root))
    except ValueError:
        return str(path)


def _extract_refs(value: Any, path: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, key)
            if (key == "ref" or key.endswith("_ref")) and isinstance(child, str):
                refs.append((".".join(child_path), child))
            else:
                refs.extend(_extract_refs(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            refs.extend(_extract_refs(child, (*path, str(index))))
    return refs


def validate_record(path: Path, layout: ProjectLayout) -> list[Result]:
    label = _label(path, layout)
    results: list[Result] = []

    try:
        with path.open("r", encoding="utf-8") as f:
            instance = json.load(f)
    except json.JSONDecodeError as e:
        results.append(("ERROR", f"{label}: 不是合法 JSON：{e}"))
        return results

    record_type = record_type_for(path)
    if record_type is None:
        results.append(
            ("ERROR", f"{label}: 無法辨識 record 類型——父目錄 {path.parent.name!r} 不在已知清單中")
        )
        return results

    if not isinstance(instance, dict):
        results.append(("ERROR", f"{label}: record 最外層必須是 JSON object"))
        return results

    schema_path = layout.schemas_dir / SUBDIR_TO_SCHEMA[record_type]
    try:
        schema = _load_schema(schema_path)
    except (json.JSONDecodeError, OSError, SchemaError, TypeError) as e:
        detail = e.message if isinstance(e, SchemaError) else str(e)
        results.append(
            ("ERROR", f"{label}: schema {schema_path.name} 本身無效：{detail}")
        )
        return results
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(map(str, e.path)))

    if errors:
        for e in errors:
            at = "/".join(str(p) for p in e.path) or "<root>"
            results.append(("ERROR", f"{label}: schema[{at}]: {e.message}"))
    else:
        results.append(("PASS", f"{label}: schema valid"))

    for field_label, ref_value in _extract_refs(instance):
        try:
            resolved = resolve_ref(layout.project_root, ref_value)
        except RefError as e:
            results.append(("ERROR", f"{label}: ref {field_label}={ref_value!r}: {e}"))
        else:
            results.append(("PASS", f"{label}: ref {field_label} -> {resolved.relative_to(layout.project_root)} resolvable"))

    return results
