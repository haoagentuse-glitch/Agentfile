## Experimental Profile

追加於 `core/AGENTS.md` 之後，只講實驗型專案（RAG、agent 架構、機器學習／深度學習、模擬、檢索與排序、最佳化、演算法比較）的特化規則，不改寫上游條文。

目標不是把分數做高，是維持實驗的可解釋性、可歸因性、可重現性與結論可信度。程式能跑不代表結論可信；這個 profile 限制的是「怎麼下結論」，不是「怎麼寫程式」。

### Experimental Engineering Rules（不變量）

1. 基準（baseline）鎖定後不得原地漂移；變更即建立新實驗／新條件。
2. 每個處理組（treatment）必須明確指出相對基準改了什麼。
3. 一次原則上只改一個主要變因；多因素實驗必須預先聲明。
4. 主要指標、評估方法、決策規則必須在看到結果前定義（見 `experiment-design`）。
5. 觀察、詮釋、結論三者分離——不得混寫成一句話。
6. 結果不好時先診斷，不得直接調參優化——用 `diagnose-experiment` 技能：探測 → 假設 → smoke 驗證 → 控制變因 → 下結論，順序不能跳。
7. 所有 run 必須留下不可覆寫紀錄，見「Canonical Records」。
8. 跑錯的 run 標記 `invalid`，不得刪除或覆蓋。
9. 比較前檢查資料集、模型、算力預算、指標算法、評估集等控制條件是否一致。
10. 有變因混雜（confounded）的比較不得產生因果性結論。
11. 結論必須能追到實驗 → run → 設定 → 程式碼／資料版本；下結論前用 `claim-audit` 技能機械核對這條鏈跟數字，語意上有沒有超出證據範圍則由 agent 判斷，見該技能。
12. 重大演算法、架構、檢索策略、模型、訓練方法、資料處理順序、關鍵超參數、評估設計的選擇，不得只依靠 agent 既有知識——先過 Research Gate。

### Research Gate

上一條列的選型範圍，動手實作前先產生一份證據回顧（做法見 `evidence-review` 技能）。證據優先序：原始論文／官方文件 → 作者的實作 → 可靠的基準測試 → 二手來源 → agent 推測（必須標 `UNVERIFIED`）。不是要寫冗長文獻回顧，目的只是避免無依據選型。

### Experiment Contract

每個實驗動手前用 `experiment-design` 技能凍結一份 Contract（`records/experiments/definitions/`），lock 後算 hash。改 `top_k`／模型／資料集／檢索預算／指標算法／評估集等控制變因不算同一個條件，必須開新條件或新實驗——用 `experiment-lint` 技能機械檢查這件事，不是自己讀過去覺得像就算數。

Contract 的 `status` 為 `locked` 時必須有 `derivation`（研究問題憑證）。lock 是開始花算力的那一刻，此時題目推導必須已可稽核。

唯一機械驗證入口：`uv run --project .agents/tools/experiment-records python -m experiment_records validate .`。
生命週期只能用 `uv run --project .agents/tools/experiment-records python -m experiment_records transition . <EXPERIMENT_ID> <TO_STATE> --reason "<REASON>"` 新增事件。不得手動覆寫既有事件。

### Provenance

agent 產生或修改的 definition、claim、audit、diagnosis 都要填 `producer`：`kind`、`name`、`model`、`prompt_id`、`prompt_hash`、`input_refs`。回溯不到 model 與 prompt 版本的 agent 產物，稽核無法重現當初的判斷。

prompt role 放 `records/experiments/prompts/<role>@<version>.md`，雜湊用 `experiment_records prompts .` 查，不要自己算。改了 prompt 內容就是新版本——沿用舊 `prompt_id` 而不更新雜湊會被 validator 擋下。

### 獨立審核

稽核的語意段不得由寫這個 claim 的同一個 context 完成。先用 `experiment_records review-package . <CLAIM_ID>` 組出審核包，它不含 `producer`，審核者看不到是誰寫的。

Contract 的 `review_policy.required_reviewer_kind` 跟 Contract 一起凍結，validator 會比對稽核紀錄的 `reviewer_kind`。看到結果之後才放寬審核標準，等於沒有審核。

### 失敗是正式結果

跑失敗、混雜、證據不足都是正式終態，不得刪除、不得改寫成弱版本的成功。失敗的 run 標 `invalid` 並填 `failure`（分類見 `failure-taxonomy.schema.json`）。走到終態時把診斷寫成 `records/experiments/diagnoses/`：確定性事實與推測分欄，並給出能分辨假設的最便宜下一步。`hypothesis_refuted` 要先排除其他分類才能用，不是兜底選項。

### Compute Gate

L0 理論／靜態檢查 → L1 合成資料／確定性測試 → L2 小型資料集 → L3 小規模試跑 → L4 消融／敏感度分析 → L5 完整規模執行。昂貴的實驗不是預設權利，沒有協調器自動幫你升級。

用 `compute-gate` 技能機械執行：不准跳級，中止條件觸發直接終止，升級條件沒滿足就擋在原地。每一級的預算、升級條件與中止條件寫在 Contract 的 `compute_cascade`，跟 Contract 一起凍結——把 `scale_up_rule`／`abort_rule` 那兩句自然語言翻成可比對的數字是寫 Contract 的人的責任，技能不自動解析；但翻譯結果必須落在 Contract 裡，不是散在某次呼叫的參數，否則同一組紀錄重跑不出同一個判定。

### Canonical Records

`records/experiments/` 是這個 profile 的持久紀錄唯一來源，只能新增不能覆寫，schema 見 `records/experiments/schemas/`。Viewer、MLflow、任何分析工具都只是使用方，不得另外維護一份權威副本（Derived Knowledge ≠ SSoT）。

### Comparability（可比較性）

比較兩個 run 前檢查資料集、評估集、指標算法、模型、隨機種子策略、算力預算、檢索預算、控制變因是否一致；有未宣告的差異就是變因混雜的比較，不得下因果性結論（見規則 9-10）。用 `compare-runs` 技能做這件事，機械判定不靠自述——沒跑這個技能不代表可以跳過檢查，手動比對一樣要照這個判準來。

### 驗證層級

TDD 只保證實作正確性，不保證結論可信。完整層級：研究有效性 → 實驗有效性 → 實作有效性 → 統計有效性 → 結論有效性。至少要有單元、不變量、合成資料、回歸測試（指標算法正確、前處理正確、固定隨機種子可重現、基準不得無故漂移）。
