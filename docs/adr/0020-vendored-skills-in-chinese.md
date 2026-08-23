# vendored 技能改寫成中文

`core/AGENTS.md` 的「技能 vendoring」要求 vendored 檔案保留上游內文，`zh-lint` 也把 vendored 目錄列為刻意不掃。同一份 `AGENTS.md` 的「輸出」節卻要求所有自然語言輸出用中文。這兩條規則在同一個工作階段裡互相牴觸：agent 讀英文技能、照中文規範辦事、再用中文回報；使用者在同一包裡讀到兩種語言的判準。

這包的定位是一個整體，不是幾個來源的拼貼。18 份技能裡有 15 份來自外部，語言不統一時，「這句是誰的規則」需要靠檔案出處判斷，而不是靠讀內容。

## 決定

### vendored 技能改寫成中文

`mattpocock/skills` 來的 12 份、`fcakyon/phd-skills` 來的 3 份，`SKILL.md` 與附屬檔案（`agents/openai.yaml`、`tdd/mocking.md` 這類）一律改寫成中文。

改寫不是逐句翻譯，是照原意重寫。**規則的數量與強度不得增減**：上游要求的步驟、順序、禁止事項一條都不能少，也不能因為中文讀起來順就多加一條。

### 保留原文的判準

原文更能表達原意時保留原文，判準如下。

- 指令、旗標、檔名、路徑、schema key、enum 值：一律原文。
- 技術術語在中文沒有廣為使用的說法：保留原文，例如 `commit`、`hook`、`schema`、`estimand`。
- 觸發語：`description` 裡的英文觸發語原樣保留。使用者打 `grill me` 或提到 `red-green-refactor` 時要照樣叫得動技能。

### `description` 是觸發器，不是說明文字

Claude Code 與 Codex 用 `description` 決定要不要載入技能。改寫時說明部分用中文，觸發語留英文，兩者並存。這一欄改壞的後果不是「讀起來怪」，是技能不會被叫起來。

### 出處與授權

- `metadata.source` 從單純的 `<repo>@<commit>` 改為 `<repo>@<commit>（改寫，非逐字保留）`。
- `docs/THIRD_PARTY_LICENSES.md` 的來源列與 MIT 全文照留。MIT 允許修改，條件是保留著作權聲明與授權條文。
- README 第三方段落的「逐字保留」字樣改成「改寫」。

### 更新程序跟著改

原本比對上游用這一行，改寫之後它永遠是滿屏差異，失去意義：

```bash
diff <(curl -sS https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md) profiles/software/skills/tdd/SKILL.md
```

改成比對上游自己的兩個 commit——`metadata.source` 記的那個，跟現在的 `main`：

```bash
diff <(curl -sS https://raw.githubusercontent.com/mattpocock/skills/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/tdd/SKILL.md) <(curl -sS https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md)
```

上游那段期間改了什麼，才是要判斷採不採納的東西。採納就改中文版並更新 `metadata.source` 的 commit。

## 拒絕的方案

### 維持現狀，vendored 保留英文

拒絕。這正是要解的問題。「逐字保留」原本的理由是「改動上游內文會讓比對失效」，但比對的目的是知道上游改了什麼，而那件事用上游對上游的 diff 就能做到，不需要本包這份也是英文。

### 中英雙語並陳

拒絕。同一條規則兩種說法，就會有兩種解讀，而且每次改都要改兩處。這是 Single Source of Truth 的反例。

### 在 `apply.sh` 投影時自動翻譯

拒絕。投影必須是確定性複製。翻譯要判斷語意，交給工具即時做，等於每次投影結果都可能不同。

### fork 上游 repo，在 fork 裡翻譯後再 vendor

拒絕。多一層要同步的東西，而且 fork 的中文版對上游社群沒有價值。這包直接持有改寫後的版本即可。

## 後果

- 一次性改寫成本約 1,200 行 Markdown 加 13 份 `agents/openai.yaml`。
- 採納上游更新變貴：要有人讀英文 diff、判斷語意變化、再改中文。這是刻意的取捨——上游更新是偶發事件，讀技能是每天的事。
- `zh-lint` 的「已知不掃」清單縮小，vendored 目錄改為要掃。
- 下游重跑 `apply.sh` 時，所有技能都會被判為更新。沒改過的自動換成中文版，改過的列進衝突等人處理。
- 改寫品質沒有機械檢查擋得住。`metadata.source` 記著來源 commit，任何一句有疑慮都回得去原文核對——這是唯一的防線，所以那個欄位不得省略。
