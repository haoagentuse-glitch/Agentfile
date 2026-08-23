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
PROJECTED_RULES = [
    ROOT / "core/AGENTS.md",
    *sorted((ROOT / "core/skills").rglob("*.md")),
    *sorted((ROOT / "core/.claude").rglob("*.md")),
    *sorted((ROOT / "profiles").glob("*/AGENTS.md")),
    *sorted((ROOT / "profiles").glob("*/skills/**/*.md")),
]

# 只在下游根目錄才成立的路徑：樣板本來就是要被複製到別處之後才解析得到。
PROJECTED_LINK_EXEMPT = {"core/.claude/templates/README.md"}

# apply.sh 只把 docs/ 底下這兩處投影出去：core/.claude/templates/agents/ 落到
# docs/agents/（apply.sh:273），以及 docs/THIRD_PARTY_LICENSES.md（apply.sh:278）。
# 其餘 docs/ 一律是上游專屬，下游不存在。
PROJECTED_DOC_PREFIXES = ("docs/agents/",)
PROJECTED_DOC_FILES = ("docs/THIRD_PARTY_LICENSES.md",)


def links_to_an_upstream_only_doc(relative: str) -> bool:
    if "docs/" not in relative:
        return False
    tail = relative[relative.index("docs/") :]
    return not (
        tail.startswith(PROJECTED_DOC_PREFIXES) or tail in PROJECTED_DOC_FILES
    )


def test_projected_rules_do_not_link_into_the_upstream_repo() -> None:
    """上游自己的 docs/ 不投影，投影文字指過去就是死連結。

    這條在 frus-agentic-rag_v2 上實際發生過三次（上游 issue #8）：投影下來的
    AGENTS.md 引用上游自己的 ADR，下游點下去什麼都沒有。

    判準是「apply.sh 有沒有把它投影出去」，不是逐條列舉已經犯過的路徑——
    列舉版每新增一份上游專屬文件就再開一次同樣的洞。
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
            if links_to_an_upstream_only_doc(relative):
                offenders.append(f"{relative_path} -> {target}")

    assert offenders == [], (
        "投影下去的規範文字用本機路徑指向上游文件，下游會拿到死連結；改用完整網址：\n"
        + "\n".join(offenders)
    )


def test_root_agents_md_keeps_the_assembled_prefix() -> None:
    """根 AGENTS.md 是手動組裝的，只有這條測試擋得住「改了 core/ 卻忘記重組」。

    apply.sh 拒絕以本包自己為目標，所以這個產物拿不到投影的更新判定；
    architecture.md 只能用一句提醒，實測時它已經漂掉一個換行。

    比對用前綴而非全等：AGENTS.md 走 prefix mode，受管前綴之後允許專案特化段，
    .gitignore 已經在用同一個機制（兩份 gitignore.base 之外還有本機 release 副本兩行）。
    全等會比 install_prefix 本身更嚴，且會禁止本包擁有每個下游都被允許擁有的東西。
    """
    assembled = (
        (ROOT / "core/AGENTS.md").read_bytes()
        + b"\n"
        + (ROOT / "profiles/software/AGENTS.md").read_bytes()
    )
    root = (ROOT / "AGENTS.md").read_bytes()

    assert root.startswith(assembled), (
        "根 AGENTS.md 的受管前綴與 core + profiles/software 的組裝結果不符。"
        "重跑組裝並保留末尾的專案特化段："
        "{ cat core/AGENTS.md; echo ''; cat profiles/software/AGENTS.md; }"
    )
