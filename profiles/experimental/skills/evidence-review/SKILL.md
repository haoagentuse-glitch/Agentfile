---
name: evidence-review
description: >
  用於選定演算法、架構、retrieval 策略、模型、訓練方法、資料處理順序、
  關鍵超參數或評估設計之前。它在任何程式寫下去之前產出一份簡短的證據回顧。
  Research Gate 名單上的項目都會觸發它——重大技術選型沒跑過這個就不要開始寫程式。
metadata:
  source: fcakyon/phd-skills@8d642d3e114ee1d1e4d000f918d71e9bf0453dc2（裁切改編後改寫成中文——搜尋方法論與引用完整性段落取自上游 literature-research，gap-analysis 與 BibTeX 產出部分整段替換，見 ADR 0006）
  license: MIT
---

# 證據回顧

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

**這條階梯只講「證據從哪來」，還要記第二軸：你是怎麼讀到它的。**

| 軸 | 值 |
|---|---|
| origin（來源） | `primary`（原始論文、官方文件、作者程式碼）／`secondary`（轉述、教學、討論）／`conjecture`（推測） |
| representation（你讀到的形式） | `direct`（讀原文本身）／`agent_summary`（讀某個工具或模型的摘要） |

一手來源的自動摘要是 `primary + agent_summary`，**不是** `primary + direct`。它看起來像一手，實際上多了一層轉述，而轉述者的偏誤看不見。實際踩過的例子：摘要寫「論文明確宣告與 CLS pooling 不相容」，原文只說「可實作在任何使用 mean pooling 的長文本嵌入模型上」——前者會直接否決一個候選，後者只是界定適用範圍。差別大到會改變選型結果。

搜尋管道：直接搜尋（多換幾種措辭，同一個概念常有不同稱呼）；citation chaining（誰引用了這篇、這篇引用了誰）；發表管道／社群動態（GitHub topic、awesome-list、Papers with Code）。

## Step 3：Citation Integrity

每個提到的來源都要可查證：

- 作者、發表年份、發表管道／repo 名稱要核對，不要憑印象
- 提到的數字（準確率、延遲、成本）只能引用能追到具體表格/章節/commit 的內容
- 不確定的地方明講不確定，不要用肯定語氣包裝猜測
- 每一筆證據都標出 origin 與 representation 兩軸，例如 `primary + agent_summary`

**會決定 Selected approach 或 Why not alternatives 的關鍵句，一律回原文定位核對。** 不是重讀摘要，是把原文抓下來、找到那句話、對字串。核對過的標成 `primary + direct`；核對不到就降級成 `secondary`，並在輸出裡寫明它沒被核對過。

判準很省事：這句話拿掉，候選的去留會不會改變？會，就核對；不會，摘要就夠用。

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
