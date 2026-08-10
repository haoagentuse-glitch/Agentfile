---
name: evidence-review
description: >
  Use before choosing an algorithm, architecture, retrieval strategy, model,
  training method, data processing order, major hyperparameter, or evaluation
  design. Produces a short evidence review before any code gets written.
  Triggers on Research Gate items — do not start coding a major technical
  choice without running this first.
metadata:
  source: fcakyon/phd-skills@8d642d3e114ee1d1e4d000f918d71e9bf0453dc2 (adapted, not verbatim — 搜尋方法論與 citation integrity 段落取自上游 literature-research，gap-analysis／BibTeX 產出部分整段替換，見 ADR 0006)
  license: MIT
---

# Evidence Review

技術選型前的證據回顧，不是文獻綜述。目的是避免無依據選型，不是找研究缺口——找到現成、可信的做法就停，不用湊齊十篇論文。

## Step 1：定義範圍

- 這次要選的是什麼（演算法／架構／retrieval 策略／model／訓練方法／資料處理順序／關鍵 hyperparameter／評估設計）
- 候選有哪些，先列出至少 2-3 個（含「什麼都不做／用現成庫預設值」這個候選，不要跳過）

## Step 2：系統性搜尋

依證據優先序找，找到高優先級的證據就不用往下找：

1. **原始論文／官方文件** — 先找一手來源，不要從二手轉述開始
2. **作者 implementation** — 官方 repo、作者釋出的程式碼
3. **可靠 benchmark** — 有獨立第三方復現或知名 leaderboard 的結果
4. **secondary source** — 部落格、教學文章、社群討論
5. **agent 推測** — 沒有以上來源支持的判斷，必須明確標 `UNVERIFIED`，不得偽裝成有依據

搜尋管道：直接搜尋（多換幾種措辭，同一個概念常有不同稱呼）；citation chaining（誰引用了這篇、這篇引用了誰）；venue／社群動態（GitHub topic、awesome-list、Papers with Code）。

## Step 3：Citation Integrity

每個提到的來源都要可查證：

- 作者、發表年份、venue／repo 名稱要核對，不要憑印象
- 提到的數字（準確率、延遲、成本）只能引用能追到具體表格/章節/commit 的內容
- 不確定的地方明講不確定，不要用肯定語氣包裝猜測

## Step 4：輸出

```
Problem: <要解決什麼問題／要做什麼選型>

Candidate A: <名稱>
Candidate B: <名稱>
Candidate C: <名稱>

Evidence:
- <來源，含優先級標記與連結／出處>
- ...

Selected approach: <選哪個>

Why not alternatives: <其他候選為什麼不選，一句話一個>

Major unknowns: <還沒被證據涵蓋、有風險的地方>

Cheapest experiment that can distinguish them: <如果證據不夠決定性，最便宜能分辨候選優劣的實驗是什麼——交給 experiment-design 技能設計>
```

不確定的候選不要硬選，寫進 Major unknowns，交給後續的 experiment 用證據分辨，不要靠猜測收斂。
