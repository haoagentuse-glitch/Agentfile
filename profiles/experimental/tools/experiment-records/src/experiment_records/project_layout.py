"""從使用者輸入的路徑（project root／records/experiments root／單一 record 檔案）
推回 (project_root, records_root, schemas_dir) 與待驗證的 record 檔案清單。

跟 viewer 的 src-tauri/src/paths.rs::resolve_project_layout 是同一個契約（project root
與 records/experiments 兩種輸入都要能推回同一組結果），這裡是 Python CLI 端的獨立實作，
不共用程式碼——兩邊語言不同、生命週期不同，共用會產生不必要的跨語言耦合。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUBDIR_TO_SCHEMA = {
    "definitions": "experiment-contract.schema.json",
    "runs": "run-envelope.schema.json",
    "comparisons": "comparison-result.schema.json",
    "claims": "claim.schema.json",
    "audits": "claim-audit-result.schema.json",
    "gates": "gate-state.schema.json",
    "metrics": "metric-definition.schema.json",
    "lifecycles": "lifecycle-state.schema.json",
}
AUXILIARY_SUBDIRS = frozenset({"schemas", "configs", "artifacts"})


class ProjectLayoutError(Exception):
    """輸入路徑無法推回一組合法的 project layout：不存在、或找不到
    records/experiments/schemas/。呼叫端必須把這個當成真正的錯誤，不能吞成空結果。"""


@dataclass(frozen=True)
class ProjectLayout:
    project_root: Path
    records_root: Path
    schemas_dir: Path


def _is_records_experiments_dir(path: Path) -> bool:
    return path.name.lower() == "experiments" and path.parent.name.lower() == "records"


def resolve_layout(start: Path) -> ProjectLayout:
    """start 必須已經是存在的絕對路徑（檔案或目錄）。"""
    base = start.parent if start.is_file() else start

    for candidate in (base, *base.parents):
        if _is_records_experiments_dir(candidate) and (candidate / "schemas").is_dir():
            records_root = candidate
            return ProjectLayout(
                project_root=candidate.parent.parent,
                records_root=records_root,
                schemas_dir=records_root / "schemas",
            )

    for candidate in (base, *base.parents):
        probe = candidate / "records" / "experiments" / "schemas"
        if probe.is_dir():
            return ProjectLayout(
                project_root=candidate,
                records_root=candidate / "records" / "experiments",
                schemas_dir=probe,
            )

    raise ProjectLayoutError(f"找不到 records/experiments/schemas/：{start}")


def collect_targets(start: Path, layout: ProjectLayout) -> list[Path]:
    """回傳待驗證的 record 檔案清單。

    目錄輸入會掃描所有非輔助子目錄，而不是只掃已知類型；如此新增或拼錯的
    record 類型會進入驗證並明確失敗，不會被靜默略過。
    """
    if start.is_file():
        try:
            start.relative_to(layout.records_root)
        except ValueError:
            raise ProjectLayoutError(
                f"單一 record 必須位於 records/experiments/ 內：{start}"
            ) from None
        return [start]

    targets: list[Path] = []
    for child in sorted(layout.records_root.iterdir()):
        if not child.is_dir() or child.name in AUXILIARY_SUBDIRS:
            continue
        targets.extend(sorted(child.glob("*.json")))
    return targets


def record_type_for(path: Path) -> str | None:
    """record 檔案所屬類型（= 父目錄名稱），對不到已知類型回傳 None。"""
    subdir = path.parent.name
    return subdir if subdir in SUBDIR_TO_SCHEMA else None
