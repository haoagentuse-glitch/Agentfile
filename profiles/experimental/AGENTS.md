## Experimental Profile

追加於 `core/AGENTS.md` 之後，只講實驗型專案（RAG、agent architecture、ML/DL、simulation、retrieval/ranking、optimization、algorithm comparison）的特化規則，不改寫上游條文。

目標不是把分數做高，是維持實驗的可解釋性、可歸因性、可重現性與結論可信度。程式能跑不代表結論可信；這個 profile 限制的是「怎麼下結論」，不是「怎麼寫程式」。

### Experimental Engineering Rules（不變量）

1. Baseline 鎖定後不得原地漂移；變更即建立新 experiment／condition。
2. 每個 treatment 必須明確指出相對 baseline 改了什麼。
3. 一次原則上只改一個主要變因；多因素實驗必須預先聲明。
4. Primary metric、evaluation method、decision rule 必須在看到結果前定義（見 `experiment-design`）。
5. Observation、Interpretation、Claim 分離——三者不得混寫成一句話。
6. 結果不好時先 diagnose，不得直接 optimize。
7. 所有 run 必須留下不可覆寫紀錄，見「Canonical Records」。
8. 跑錯的 run 標記 `invalid`，不得刪除或覆蓋。
9. 比較前檢查 dataset、model、budget、metric schema、evaluation set 等控制條件是否一致。
10. Confounded comparison 不得產生因果性 claim。
11. Claim 必須能追到 experiment → run → config → code/data version。
12. 重大算法、架構、retrieval 策略、model、訓練方法、資料處理順序、關鍵 hyperparameter、評估設計的選擇，不得只依靠 agent 既有知識——先過 Research Gate。

### Research Gate

上一條列的選型範圍，動手實作前先產生一份 evidence review（做法見 `evidence-review` 技能）。證據優先序：原始論文／官方文件 → 作者 implementation → 可靠 benchmark → secondary source → agent 推測（必須標 `UNVERIFIED`）。不是要寫冗長 literature review，目的只是避免無依據選型。

### Experiment Contract

每個 experiment 動手前用 `experiment-design` 技能凍結一份 Contract（`records/experiments/definitions/`），lock 後算 hash。改 `top_k`／model／dataset／retrieval budget／metric 實作／evaluation set 等 controlled variable 不算同一個 condition，必須開新 condition 或新 experiment——用 `experiment-lint` 技能機械檢查這件事，不是自己讀過去覺得像就算數。

### Compute Gate

L0 理論／靜態檢查 → L1 synthetic/deterministic → L2 tiny dataset → L3 small pilot → L4 ablation/sensitivity → L5 full run。往上升級要 Contract 裡的 `scale_up_rule` 允許，不是「看起來有戲就繼續跑」；沒有 orchestrator 自動幫你升級，人或呼叫的 agent 自己讀規則判斷。昂貴 experiment 不是預設權利。

### Canonical Records

`records/experiments/` 是這個 profile 的持久紀錄唯一來源，append-only，schema 見 `records/experiments/schemas/`。Viewer、MLflow、任何分析工具都是 consumer，不得另外維護一份權威副本（Derived Knowledge ≠ SSoT）。

### Comparability

比較兩個 run 前檢查 dataset、evaluation set、metric schema、model、seed policy、compute budget、retrieval budget、controlled variables 是否一致；有未宣告差異就是 confounded comparison，不得下因果性結論（見規則 9-10）。自動化比對工具是 Phase C 的 `compare-runs`，這輪還沒做——沒有工具不代表可以跳過人工檢查。

### 驗證層級

TDD 只保證 implementation validity，不保證結論可信。完整層級：Research validity → Experiment validity → Implementation validity → Statistical validity → Claim validity。至少要有 unit／invariant／synthetic／regression tests（metric 實作正確、preprocessing 正確、固定 seed 可重現、baseline 不得無故漂移）。
