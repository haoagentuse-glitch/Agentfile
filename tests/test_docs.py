"""使用者會讀到的 Markdown 本機連結必須能解析。"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def public_docs() -> list[Path]:
    return [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
        ROOT / "profiles/experimental/fixtures/rag-walkthrough/README.md",
        ROOT / "viewer/experiment-viewer/README.md",
    ]


def test_local_markdown_links_resolve() -> None:
    broken: list[str] = []
    for document in public_docs():
        for raw_target in LINK.findall(document.read_text(encoding="utf-8")):
            target = raw_target.strip().strip("<>")
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative = unquote(target.split("#", 1)[0])
            if not relative:
                continue
            if not (document.parent / relative).resolve().exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")

    assert broken == [], "找不到本機文件連結：\n" + "\n".join(broken)
