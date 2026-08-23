---
name: experiment-design
description: >
  用於使用者要設計實驗、規劃消融研究、安排基準組，或建立分階段評估策略的時候。
  觸發語包括「設計消融」、「規劃實驗」、「我該跑哪些實驗」、「基準比較」、
  「實驗矩陣」，以及 design ablation、plan experiment、experiment matrix。
metadata:
  source: fcakyon/phd-skills@8d642d3e114ee1d1e4d000f918d71e9bf0453dc2（裁切改編後改寫成中文——Step 1-4 與 6、驗證檢查點取自上游；第 5 步的可行性檢查、第 7-8 步與輸出格式為本包自寫，見 ADR 0006 與 ADR 0021）
  license: MIT
---

# 實驗設計方法論

你在協助研究者設計嚴謹的實驗。照這套方法論一步一步走。

## 第 1 步：弄清楚研究問題

設計任何實驗之前：

- 問清楚這個實驗要支撐的是哪一個具體假說或主張
- 指出應變數（指標）與自變數（因子）
- 釐清基準：目前最好的結果或預設設定是什麼？
- 這是演算法／架構／retrieval 策略等重大選型的話，先跑過 `evidence-review`，不要跳過 Research Gate 直接設計實驗。

## 第 2 步：單一變因隔離

每個消融研究一次只能動**一個**變因。每個因子都要：

1. **定義因子**——被改動的是什麼（例如損失函數、學習率、架構元件）
2. **列出層級**——這個因子會取的所有值（例如 CE、focal、VAR）
3. **固定其餘一切**——寫下什麼維持不變（seed、資料切分、epoch、硬體）→ 這會成為 Contract 裡的 `controlled_variables`
4. **預測結果**——開跑之前先說出你預期什麼、為什麼

多因素研究要在 Contract 裡明講是多因素設計，不能事後才承認改了不只一個變因。

## 第 3 步：實驗矩陣

多因素研究要用結構化的矩陣：

1. **完全因子設計**——因子少（≤3）且每個因子的層級也少（≤3）時
2. **序列淘汰**——因子多的時候：先跑單因子消融，再把贏的組合起來
3. **拉丁方格**——完全因子太貴時：抽有代表性的組合

投入之前一律先算總 run 數：

```
總 run 數 = 所有因子層級的乘積
計算時數 = 總 run 數 × 每個 run 的時數
```

## 第 4 步：資源估算 → compute_budget

填 Contract 的 `compute_budget`：

- **pilot_max_minutes** / **pilot_max_samples**：pilot 規模的硬上限，不是「先跑跑看」
- 完整規模的預估（計算時數、API 成本、實際時間、儲存空間）供 `scale_up_rule` 判斷要不要升級
- 超出合理範圍就在 Contract 的 `abort_rule` 寫清楚什麼情況要喊停，不是跑到天荒地老

## 第 5 步：可行性檢查——凍結的規格湊不湊得出來

結構檢查擋不住算術上界。「四卷子集」配「每個題型抽 500 題」看起來都合法，但那四卷合計只有 304 題時，任何組合都取不到 500——這不是估計偏差，是不可能。

**資料抽樣型的實驗，lock 前要實際量一次供給。** 跑一道具名命令，把結果寫進 Contract 的 `feasibility_checks`：

```json
{
  "name": "gold 每卷供給足以支撐 stratified-500-per-kind",
  "command": "frus gold-shape --by volume --kind topic",
  "evidence_ref": "docs/evidence/gold-supply.md",
  "passed": true
}
```

四個欄位缺一不可：沒有 `command` 就重跑不出來，沒有 `evidence_ref` 就查不到當初看到什麼，沒有 `passed` 就不知道結論，沒有 `name` 就不知道它在回答哪個疑慮。

**會影響規模的數字必須落在結構化設定裡。** `derivation` 的散文寫「四卷」，而設定層沒有卷數這個鍵，兩者之間就沒有任何工具連得起來——validator 不會、也不該從散文猜數字。要嘛把卷數升成明列的控制變因，要嘛承認它不受管。

validator 只檢查已宣告的 `feasibility_checks` 完不完整、`evidence_ref` 解不解析得到。它判斷不出你的設計是不是抽樣型，所以「有沒有做這個檢查」是寫 Contract 的人的責任。理由見 [ADR 0021](../../../docs/adr/0021-metric-validity-and-feasibility-checks.md)。

## 第 6 步：產生設定檔骨架

產出的設定骨架要對得上使用者既有的設定格式。先讀既有設定，對齊檔案格式、鍵的命名、目錄結構與既有的 tracking 整合。`baseline.config_ref` 與 `treatment.config_ref` 指向這兩份實際存在的設定檔，不是描述。

## 第 7 步：凍結 Experiment Contract

把上面的決定寫成一份符合 `records/experiments/schemas/experiment-contract.schema.json` 的 JSON，存到 `records/experiments/definitions/<experiment_id>.json`，`status` 設 `draft`。

跑 `experiment-lint`（見該技能）驗證：必填欄位齊全、baseline 跟 treatment 的設定檔之間沒有 `controlled_variables` 以外的未宣告差異。lint 沒過不要 lock。

過了以後把 `status` 改成 `locked`，跑 `uv run --project .agents/tools/experiment-records python -m experiment_records contract-hash <definition> --write` 算出 `contract_hash` 並寫回——不要手算，雜湊用 RFC 8785 正規化，手算會對不上。lock 之後這份檔案不得再改——要改 `top_k`、模型、資料集、`compute_budget`、metric 實作或評估集等任何一項，開新的 `experiment_id` 或新的 treatment 條件，不得原地覆寫。

## 第 8 步：分析計畫

開跑之前先定義結果要怎麼分析，寫進 Contract 或隨 run 記錄：

- 對應 primary／secondary metric（見 `records/experiments/schemas/metric-definition.schema.json`，metric 的實際算法要版本化）
- 適用時的統計顯著性檢定（paired t-test、bootstrap CI）
- `decision_rule` 已經在 Contract 裡凍結，分析階段不得為了讓結果好看而改判準
- 每個 run 的紀錄格式見 `run-envelope.schema.json`；跑錯的 run 標 `invalid` 並填 `invalid_reason`，不得刪除

## 驗證檢查點

把實驗計畫定案之前：

- [ ] 每個消融只動一個變因（或已明確聲明為多因素設計）
- [ ] 基準組定義清楚，而且會用同一套環境跑
- [ ] `compute_budget`／`abort_rule`／`scale_up_rule` 都填了
- [ ] 設定骨架對得上專案既有格式，`config_ref` 指向真實存在的檔案
- [ ] 抽樣型設計已實跑供給檢查，結果寫進 `feasibility_checks`；影響規模的數字在結構化設定裡有對應的鍵
- [ ] primary metric 與所有 Compute Gate 門檻引用的指標，`validity.threshold_eligible` 都是 true
- [ ] `experiment-lint` 通過，`contract_hash` 已計算
- [ ] seed 已固定，可重現

## 輸出

1. **Experiment Contract**（寫入 `records/experiments/definitions/<experiment_id>.json`，lock 後帶 hash）
2. **實驗矩陣表**——所有 run 與各自的設定（給人看的摘要，權威版本是 Contract 本身）
3. **資源估算**——計算時數、API 成本、儲存空間
4. **下一步**：告訴使用者要跑 `experiment-lint` 驗證 Contract，通過才開始執行 run
