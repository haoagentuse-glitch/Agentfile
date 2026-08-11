"""解析 Schema 以 `format: project-ref` 宣告的欄位。所有 ref 統一視為 project-root-relative、
以 `/` 序列化——不是相對於引用它的檔案的目錄（舊版 experiment_lint.py／
compare_runs.py 是後者，這裡刻意換成更嚴格、跟 claim.comparison_ref 既有慣例
一致的規則，因為 config_ref 相對於檔案目錄、comparison_ref 相對於 project root
兩種慣例並存正是目前 fixture 裡已經出現的不一致，這個新套件不重蹈覆轍）。

拒絕四類輸入，語意對齊 viewer 的 src-tauri/src/paths.rs::resolve_within_root：
POSIX 絕對路徑、Windows 絕對路徑／drive prefix／UNC、`..` 跳脫、
canonicalize 後仍跳脫 project root 範圍（含 symlink 跳脫）。
"""

from __future__ import annotations

import re
from pathlib import Path

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


class RefError(Exception):
    """base class；呼叫端通常不需要分 Invalid／NotFound，都是驗證失敗。"""


class RefInvalid(RefError):
    """ref 字串本身形狀不合法（絕對路徑、drive/prefix、`..`、跳脫 project root）。"""


class RefNotFound(RefError):
    """ref 形狀合法，但解析後的檔案不存在。"""


def validate_ref_syntax(ref: str) -> None:
    """驗證可由 Schema format 表達、不需檔案系統的 ref 規則。"""
    if not ref:
        raise RefInvalid("ref 不可為空字串")

    if "\\" in ref:
        raise RefInvalid(f"ref 必須以 / 序列化，不可包含反斜線：{ref!r}")

    if ref.startswith("/"):
        raise RefInvalid(f"ref 不可是 POSIX 絕對路徑：{ref!r}")

    if _WINDOWS_DRIVE.match(ref):
        raise RefInvalid(f"ref 不可包含 Windows drive/prefix：{ref!r}")

    if any(segment == ".." for segment in ref.split("/")):
        raise RefInvalid(f"ref 不可包含 .. 跳脫：{ref!r}")


def resolve_ref(project_root: Path, ref: str) -> Path:
    validate_ref_syntax(ref)
    root_resolved = project_root.resolve(strict=True)
    joined = project_root / ref
    try:
        resolved = joined.resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError):
        raise RefNotFound(f"ref 指到的檔案不存在：{ref!r}") from None

    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise RefInvalid(f"ref 解析後跳脫 project root 範圍：{ref!r}")

    return resolved
