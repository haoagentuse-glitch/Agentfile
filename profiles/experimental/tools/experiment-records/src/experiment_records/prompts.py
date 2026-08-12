"""版本化 prompt role 的登錄與雜湊。

prompt 是最常被當成隱藏設定的東西：內容改了、輸出跟著變，但沒有任何欄位記錄這件事。
這裡把 prompt 檔案的內容雜湊變成可機械比對的值，讓 provenance 裡的 prompt_hash
真的有東西可以對。

prompt 檔案放 `records/experiments/prompts/<role>@<version>.md`，跟 configs/ 一樣是
records root 底下的輔助資料，不是 record 類型。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from experiment_records.project_layout import ProjectLayout

PROMPTS_SUBDIR = "prompts"
PROMPT_ID = re.compile(r"^[a-z0-9][a-z0-9-]*@[0-9]+$")


def prompts_dir(layout: ProjectLayout) -> Path:
    return layout.records_root / PROMPTS_SUBDIR


def prompt_path(layout: ProjectLayout, prompt_id: str) -> Path | None:
    """prompt_id 對應的檔案；格式不合或檔案不存在就回 None。

    回 None 代表「這個 prompt 不由本專案管理」，不是錯誤——專案可以用自己的
    prompt，此時 prompt_hash 沒有可比對的來源，驗證只能略過。
    """
    if not PROMPT_ID.match(prompt_id):
        return None
    candidate = prompts_dir(layout) / f"{prompt_id}.md"
    return candidate if candidate.is_file() else None


def hash_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def known_prompts(layout: ProjectLayout) -> dict[str, str]:
    """本專案管理的 prompt role → 內容雜湊，依 prompt_id 排序。"""
    directory = prompts_dir(layout)
    if not directory.is_dir():
        return {}
    return {
        path.stem: hash_file(path)
        for path in sorted(directory.glob("*.md"))
        if PROMPT_ID.match(path.stem)
    }
