from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from helpers import valid_metric

# Contract 引用的指標必須解析得到定義，所以乾淨專案要先有 valid_definition() 用到的兩份。
DEFAULT_METRICS = ("recall_at_10", "latency_ms")


def _find_canonical_schemas() -> Path:
    for candidate in Path(__file__).resolve().parents:
        probe = candidate / "records" / "experiments" / "schemas"
        if probe.is_dir():
            return probe
    raise RuntimeError("找不到 records/experiments/schemas/")


CANONICAL_SCHEMAS = _find_canonical_schemas()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """建立已含 canonical schemas 與預設 metric 定義的乾淨專案根目錄。"""
    schemas_dir = tmp_path / "records" / "experiments" / "schemas"
    schemas_dir.mkdir(parents=True)
    for schema_file in CANONICAL_SCHEMAS.glob("*.json"):
        shutil.copy(schema_file, schemas_dir / schema_file.name)

    metrics_dir = tmp_path / "records" / "experiments" / "metrics"
    metrics_dir.mkdir(parents=True)
    for name in DEFAULT_METRICS:
        (metrics_dir / f"{name}.json").write_text(
            json.dumps(valid_metric(name=name), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return tmp_path