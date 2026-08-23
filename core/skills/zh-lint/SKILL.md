---
name: zh-lint
description: >
  用在這包擁有的中文散文檔定稿之前（docs/、ADR、README、技能檔）——掃出
  AGENTS.md 語言規則該翻成中文、卻留著的英文詞。它不是完整的語言檢查，
  只抓已經被抓到過的真實錯誤。觸發語：「自查中英夾雜」、「檢查中英夾雜」、
  check for mixed language。
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

- **`core/.claude/templates/agents/issue-tracker.md`**：GitHub Issue 與 label 的操作樣板，內容幾乎全是 `gh` 指令與 label 名稱，剩下的散文極少，翻了也只是把指令的說明文字改語言。
- **`.memsearch/memory/`**：memsearch 自己的擷取流程產生的逐字稿摘要，不是這包手寫的文件，不歸這條規則管，也不該手動改——改了下次索引照樣蓋掉。

vendored skill 本體**不**在排除之列。[ADR 0020](../../../docs/adr/0020-vendored-skills-in-chinese.md) 之後它們都是中文，跟自寫技能一樣要掃。

真的要對整個 repo 跑一次，記得把上面這幾類路徑排除，不然會撈到一堆不該修、也修不動的假警報。
