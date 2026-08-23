"""紀錄層的唯一入口：把 `records/experiments/` 讀成一份可查詢的 snapshot。

在這之前，每個檢查各自開檔、各自 glob、各自解析 JSON，而「這份紀錄屬於哪個
experiment」這個判斷散在三個地方。這裡把它收成一處。

ProjectSnapshot 只回答「有哪些紀錄，它們怎麼互指」：載入、record ID index、
跨 record 參照、dependency closure、contract hash 與共用資格檢查。

它不含比較演算法、不含 Compute Gate、不含生命週期狀態機——那三者回答的是
「這些數字代表什麼」，各自有擁有者。理由見 ADR 0016。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from experiment_records.canonical_json import canonicalize, loads_strict
from experiment_records.project_layout import (
    ProjectLayout,
    collect_targets,
    record_type_for,
    resolve_layout,
)

CONTRACT_HASH_FIELD = "contract_hash"

# 每種紀錄拿哪個欄位當 ID。沒列的用檔名，不憑空造一個。
_ID_FIELD = {
    "definitions": "experiment_id",
    "runs": "run_id",
    "claims": "claim_id",
    "audits": "claim_id",
    "gates": "experiment_id",
    "metrics": "name",
    "lifecycles": "event_id",
}


def contract_hash(document: dict[str, Any]) -> str:
    """Contract 的正規雜湊：移除頂層 contract_hash，RFC 8785 正規化，SHA-256。

    排除欄位本身是必要的——否則填進去的值會影響下一次計算，永遠對不上自己。
    """
    payload = {key: value for key, value in document.items() if key != CONTRACT_HASH_FIELD}
    return hashlib.sha256(canonicalize(payload)).hexdigest()


@dataclass(frozen=True)
class Record:
    """一筆已載入的紀錄。`data` 為 None 代表載不進來，原因記在 `problem`。"""

    path: Path
    label: str
    record_type: str | None
    record_id: str
    experiment_id: str | None
    data: dict[str, Any] | None
    problem: str | None


@dataclass(frozen=True)
class ProjectSnapshot:
    layout: ProjectLayout
    records: tuple[Record, ...]
    targets: tuple[Record, ...]
    # (record_type, record_id) -> Record，first-write-wins（跟原本線性掃描的
    # first-match 語意一致）。scoped_to 換的是 targets，records 不變，重建一次
    # 索引的成本跟原本掃一次的成本同量級，不必額外做快取重用。
    _by_key: dict[tuple[str, str], Record] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _by_path: dict[Path, Record] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        by_key: dict[tuple[str, str], Record] = {}
        by_path: dict[Path, Record] = {}
        for candidate in self.records:
            by_path.setdefault(candidate.path, candidate)
            if candidate.record_type is not None:
                by_key.setdefault((candidate.record_type, candidate.record_id), candidate)
        object.__setattr__(self, "_by_key", by_key)
        object.__setattr__(self, "_by_path", by_path)

    def of_type(self, record_type: str) -> tuple[Record, ...]:
        return tuple(record for record in self.records if record.record_type == record_type)

    def record(self, record_type: str, record_id: str) -> Record | None:
        return self._by_key.get((record_type, record_id))

    def record_at(self, path: Path) -> Record | None:
        return self._by_path.get(path)

    def metric_defined(self, name: str) -> bool:
        return self.record("metrics", name) is not None

    def metric_threshold_eligible(self, name: str) -> bool:
        """這個 metric 有沒有資格承載判定門檻。查得到定義、且它自己說 true 才算。

        缺 validity 整塊、或 threshold_eligible 不是 true，一律回 false——
        「還沒驗證過」與「驗證過但不適合當門檻」在這裡是同一件事：不能掛門檻。
        """
        metric = self.record("metrics", name)
        if metric is None or not isinstance(metric.data, dict):
            return False
        validity = metric.data.get("validity")
        return isinstance(validity, dict) and validity.get("threshold_eligible") is True

    def closure(self, experiment_id: str) -> tuple[Record, ...]:
        """一個 experiment 的全部相關紀錄，含它引用的 metric 定義。

        歸屬不明的紀錄（JSON 壞掉、類型不明、缺 experiment_id）不進任何 closure。
        validate 會報告它們；transition 不該被它們擋住。
        """
        selected = {
            record.path for record in self.records if record.experiment_id == experiment_id
        }
        for name in self._cited_metrics(experiment_id):
            metric = self.record("metrics", name)
            if metric is not None:
                selected.add(metric.path)
        return tuple(record for record in self.records if record.path in selected)

    def scoped_to(self, targets: tuple[Record, ...]) -> ProjectSnapshot:
        """換一組驗證目標，可見的紀錄不變——範圍變的是操作，不是事實。"""
        return ProjectSnapshot(layout=self.layout, records=self.records, targets=targets)

    def semantic_review_applicable(self, audit: dict[str, Any]) -> bool:
        """機械檢查沒過時，語意審核與 reviewer policy 為不適用，不是缺漏。

        工具自己就會印「不需要再判斷 scope」。同一個工具不該一邊說不必審，
        一邊要求提供獨立審核者的身分。
        """
        mechanical = audit.get("mechanical")
        if not isinstance(mechanical, dict):
            return True
        return mechanical.get("mechanical_pass") is not False

    def expected_contract_hash(self, document: dict[str, Any]) -> str:
        return contract_hash(document)

    def _cited_metrics(self, experiment_id: str) -> list[str]:
        contract = self.record("definitions", experiment_id)
        if contract is None or contract.data is None:
            return []
        cited = [contract.data.get("primary_metric")]
        cited.extend(contract.data.get("secondary_metrics", []))
        return [name for name in cited if isinstance(name, str)]


def load_project(start: Path) -> ProjectSnapshot:
    """start 可以是 project root、records/experiments 或單一 record 檔案。

    無論輸入是什麼，`records` 一律是全專案；`targets` 才是這次輸入指到的子集。
    跨 record 判斷需要看得見全部紀錄，否則「這份證據屬於別的 experiment」這種
    錯誤會因為看不到對方而漏掉。
    """
    layout = resolve_layout(start)
    targets = collect_targets(start, layout)
    all_paths = collect_targets(layout.records_root, layout)
    if start.is_file() and start not in all_paths:
        all_paths = [*all_paths, start]

    records = _load_records(all_paths, layout)
    by_path = {record.path: record for record in records}
    return ProjectSnapshot(
        layout=layout,
        records=tuple(records),
        targets=tuple(by_path[path] for path in targets if path in by_path),
    )


def _load_records(paths: list[Path], layout: ProjectLayout) -> list[Record]:
    records = [_load_record(path, layout) for path in paths]
    _attach_audit_experiments(records)
    return records


def _load_record(path: Path, layout: ProjectLayout) -> Record:
    record_type = record_type_for(path)
    try:
        data = loads_strict(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as error:
        return _record(path, layout, record_type, None, f"不是合法 JSON：{error}")
    except OSError as error:
        return _record(path, layout, record_type, None, f"讀不到檔案：{error}")
    if not isinstance(data, dict):
        return _record(path, layout, record_type, None, "record 最外層必須是 JSON object")
    return _record(path, layout, record_type, data, None)


def _record(
    path: Path,
    layout: ProjectLayout,
    record_type: str | None,
    data: dict[str, Any] | None,
    problem: str | None,
) -> Record:
    record_id = path.stem
    experiment_id: str | None = None
    if data is not None:
        field = _ID_FIELD.get(record_type or "")
        if field is not None and isinstance(data.get(field), str):
            record_id = data[field]
        if record_type != "metrics" and isinstance(data.get("experiment_id"), str):
            experiment_id = data["experiment_id"]
    return Record(
        path=path,
        label=_label(path, layout),
        record_type=record_type,
        record_id=record_id,
        experiment_id=experiment_id,
        data=data,
        problem=problem,
    )


def _attach_audit_experiments(records: list[Record]) -> None:
    """audit 沒有 experiment_id，它經由 claim_id 歸屬到 experiment。"""
    claims = {
        record.record_id: record.experiment_id
        for record in records
        if record.record_type == "claims"
    }
    for index, record in enumerate(records):
        if record.record_type != "audits" or record.experiment_id is not None:
            continue
        experiment_id = claims.get(record.record_id)
        if experiment_id is not None:
            records[index] = replace(record, experiment_id=experiment_id)


def _label(path: Path, layout: ProjectLayout) -> str:
    try:
        return str(path.relative_to(layout.project_root))
    except ValueError:
        return str(path)
