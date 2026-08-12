from __future__ import annotations

import shutil
from pathlib import Path

import pytest


def _find_canonical_schemas() -> Path:
    for candidate in Path(__file__).resolve().parents:
        probe = candidate / "records" / "experiments" / "schemas"
        if probe.is_dir():
            return probe
    raise RuntimeError("找不到 records/experiments/schemas/")


CANONICAL_SCHEMAS = _find_canonical_schemas()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """建立已含 canonical schemas 的乾淨專案根目錄。"""
    schemas_dir = tmp_path / "records" / "experiments" / "schemas"
    schemas_dir.mkdir(parents=True)
    for schema_file in CANONICAL_SCHEMAS.glob("*.json"):
        shutil.copy(schema_file, schemas_dir / schema_file.name)
    return tmp_path