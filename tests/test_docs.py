"""目前文件與建置後發行包的本機連結必須能解析。"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentfile.distribution import build_distributions  # noqa: E402

LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _broken_links(root: Path, documents: list[Path]) -> list[str]:
    broken: list[str] = []
    for document in documents:
        for raw_target in LINK.findall(document.read_text(encoding="utf-8")):
            target = raw_target.strip().strip("<>")
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative = unquote(target.split("#", 1)[0])
            if relative and not (document.parent / relative).resolve().exists():
                broken.append(f"{document.relative_to(root)} -> {target}")
    return broken


def test_repository_markdown_links_resolve() -> None:
    documents = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
        ROOT / "examples/experimental/rag-walkthrough/README.md",
        ROOT / "viewer/experiment-viewer/README.md",
    ]

    assert _broken_links(ROOT, documents) == []


def test_built_profiles_have_no_dead_local_markdown_links(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    build_distributions(ROOT / "agentfile.toml", output)

    broken: list[str] = []
    for profile in sorted(path for path in output.iterdir() if path.is_dir()):
        documents = [
            profile / "AGENTS.md",
            profile / "CLAUDE.md",
            *sorted((profile / "docs").rglob("*.md")),
        ]
        broken.extend(_broken_links(profile, documents))

    assert broken == []


def test_root_agents_only_governs_agentfile_repository() -> None:
    body = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "Agentfile 維護規則" in body
    assert "packages/core-superpowers" in body
    assert "@.agents/skills/using-superpowers" not in body
