---
name: zh-lint
description: >
  Use before finalizing any Chinese prose file this pack owns (docs/, ADR,
  README, self-authored SKILL.md) — scans for known English filler words that
  should be translated per AGENTS.md's language rule. Not a full language
  checker, only catches words already caught as real mistakes. Triggers on
  "check for mixed language", "自查中英夾雜".
---

# zh-lint

`AGENTS.md`「輸出」節要求對使用者的一切輸出使用中文，但「先自己複查一遍再定稿」這個紀律在這個包的實際歷史裡失守過不只一次——同一個字（`funnel`）被抓到三次。這個技能是 Institutionalize Repeated Failures 原則的直接示範：同類失誤反覆發生、有具體證據，才把它變成機械檢查。

## 用法

```bash
python3 core/skills/zh-lint/zh_lint.py <file1.md> [file2.md ...]
```

exit code 0 = 乾淨，1 = 抓到至少一處。這是提醒用的 lint，不是擋 commit 的硬性 gate——這包沒有 CI，跑不跑、改不改由你自己判斷。

只設計給 Markdown 用：排除的是 frontmatter／fenced code block／inline code 這幾種 Markdown 語法。拿去掃 `.py`／`.json` 這類原始碼檔案會誤判——整份檔案沒有 Markdown 圍欄可以排除，字串常數跟註解裡的技術詞會被當成散文抓到（例如這支腳本自己的 `wordlist.json` 索引邏輯裡的 `"budget"` 字面值）。

## 白名單怎麼長大

`wordlist.json` 只收這個包實際犯過、被抓到的詞（`funnel`、`confirm`、`orchestrator`、`deterministic`……），不是預先列一份「所有可能的英文技術詞」的完整字典——那樣會抓到大量像 `run`、`commit`、`API`、`hook` 這種這包刻意保留原文的通行技術詞，變成每次都要人工篩選的噪音，反而沒人想跑。抓到新的真違規，就加進 `wordlist.json`；抓到系統性誤判（例如 `budget` 同時是散文詞跟「Context Budget」這種本包自訂的專有名詞），改 `zh_lint.py` 裡的排除邏輯，不要為了怕誤判就整條規則拿掉。

## 已知不掃的東西（不是漏掃，是刻意排除）

- **vendored skill 本體**（`core/skills/grilling/` 這類、AGENTS.md 職責邊界表以外的既有 vendored 目錄）：`vendored 檔案不翻譯` 是既有規則，這些檔案本來就該是英文。
- **延伸 vendored 生態系的檔案**，例如 `core/.claude/templates/agents/issue-tracker.md`：內容配合英文 vendored skill（`to-spec`／`to-tickets`）一起讀，維持一致比逐檔硬翻更重要。
- **`.memsearch/memory/`**：memsearch 自己的擷取流程產生的逐字稿摘要，不是這包手寫的文件，不歸這條規則管，也不該手動改——改了下次索引照樣蓋掉。

真的要對整個 repo 跑一次，記得把上面這幾類路徑排除，不然會撈到一堆不該修、也修不動的假警報。
