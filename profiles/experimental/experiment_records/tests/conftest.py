from __future__ import annotations

import shutil
from pathlib import Path

import pytest

CANONICAL_SCHEMAS = (
    Path(__file__).resolve().parent.parent.parent / "records" / "experiments" / "schemas"
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """一個乾淨的專案根目錄，已放好 records/experiments/schemas/（複製自本包的
    canonical schema，跟 apply.sh 投影到目標專案時的結果一致）。"""
    schemas_dir = tmp_path / "records" / "experiments" / "schemas"
    schemas_dir.mkdir(parents=True)
    for f in CANONICAL_SCHEMAS.glob("*.json"):
        shutil.copy(f, schemas_dir / f.name)
    return tmp_path
