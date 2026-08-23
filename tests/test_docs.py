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


# 投影到下游的規範文字裡，本機連結必須指得到下游真的有的東西。
# 上游自己的 docs/adr/ 與 docs/architecture.md 不投影，所以引用它們一律用完整網址。
PROJECTED_RULES = [
    ROOT / "core/AGENTS.md",
    *sorted((ROOT / "core/skills").rglob("*.md")),
    *sorted((ROOT / "core/.claude").rglob("*.md")),
    *sorted((ROOT / "profiles").glob("*/AGENTS.md")),
    *sorted((ROOT / "profiles").glob("*/skills/**/*.md")),
]

# 只在下游根目錄才成立的路徑：樣板本來就是要被複製到別處之後才解析得到。
PROJECTED_LINK_EXEMPT = {"core/.claude/templates/README.md"}


def test_projected_rules_do_not_link_into_the_upstream_repo() -> None:
    """下游拿不到 docs/adr/ 與 docs/architecture.md，指過去就是死連結。

    這條在 frus-agentic-rag_v2 上實際發生過三次（上游 issue #8）：投影下來的
    AGENTS.md 引用上游自己的 ADR，下游點下去什麼都沒有。
    """
    offenders: list[str] = []
    for document in PROJECTED_RULES:
        relative_path = str(document.relative_to(ROOT))
        if relative_path in PROJECTED_LINK_EXEMPT:
            continue
        body = document.read_text(encoding="utf-8")
        for raw_target in LINK.findall(body):
            target = raw_target.strip().strip("<>")
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative = unquote(target.split("#", 1)[0])
            if "docs/adr/" in relative or relative.endswith("docs/architecture.md"):
                offenders.append(f"{relative_path} -> {target}")

    assert offenders == [], (
        "投影下去的規範文字用本機路徑指向上游文件，下游會拿到死連結；改用完整網址：\n"
        + "\n".join(offenders)
    )
