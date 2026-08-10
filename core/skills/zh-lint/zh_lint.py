#!/usr/bin/env python3
"""掃中文文件裡有沒有夾雜已知該翻譯卻沒翻的英文字。

用法：
  python3 zh_lint.py <file.md> [file2.md ...]

白名單（wordlist.json）只收這個包實際犯過、被抓到的詞，不是預先猜的完整字典
——這支工具本身就是 Institutionalize Repeated Failures 的示範：同類失誤反覆
發生且有具體證據，才把它變成機械檢查，不是預先假設所有可能的英文字都要擋。

排除 frontmatter、fenced code block、inline code span——那些本來就允許原文
（vendored 檔案、程式碼識別符）。用等長空白取代被排除的內容，保留行號跟欄位
不跑掉，不是直接砍字串。

exit code：0 = 乾淨，1 = 抓到至少一個。這是提醒用的 lint，不是擋 commit 的
硬性 gate——這包沒有 CI，跑不跑由你自己決定，抓到不代表一定要改（vendored
內容、專有名詞誤判都可能是合理例外）。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORDLIST_PATH = Path(__file__).resolve().parent / "wordlist.json"

FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def blank_out(text: str, pattern: re.Pattern) -> str:
    """把 pattern 命中的內容換成等長空白（換行符保留），行號跟欄位不跑掉。"""
    def repl(m: re.Match) -> str:
        return "".join(c if c == "\n" else " " for c in m.group(0))
    return pattern.sub(repl, text)


def scan(path: Path, wordlist: dict[str, str]) -> list[tuple[int, str, str]]:
    text = path.read_text(encoding="utf-8")
    cleaned = blank_out(text, FRONTMATTER_RE)
    cleaned = blank_out(cleaned, FENCE_RE)
    cleaned = blank_out(cleaned, INLINE_CODE_RE)

    hits: list[tuple[int, str, str]] = []
    for word, translation in wordlist.items():
        for m in re.finditer(r"(?<![a-zA-Z])" + re.escape(word) + r"(?![a-zA-Z])", cleaned, re.IGNORECASE):
            if word.lower() == "budget" and cleaned[max(0, m.start() - 8):m.start()].endswith("Context "):
                continue  # Context Budget 是這包自己定義的原則名稱，不是待翻譯的散文詞
            line_no = cleaned.count("\n", 0, m.start()) + 1
            hits.append((line_no, m.group(0), translation))
    return sorted(hits)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python3 zh_lint.py <file.md> [file2.md ...]", file=sys.stderr)
        return 2

    wordlist = json.loads(WORDLIST_PATH.read_text(encoding="utf-8"))
    total = 0
    for arg in sys.argv[1:]:
        path = Path(arg)
        hits = scan(path, wordlist)
        for line_no, word, translation in hits:
            print(f"{path}:{line_no}: {word!r} 建議翻成「{translation}」")
        total += len(hits)

    if total == 0:
        print("乾淨，沒抓到白名單裡的詞。")
        return 0
    print(f"\n共 {total} 處。抓到不代表一定要改（vendored 內容、專有名詞誤判都可能是合理例外），但先看一眼。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
