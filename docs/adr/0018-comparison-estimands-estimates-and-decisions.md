# Comparison 的 estimand、estimate 與 decision

現有 comparison 只保存 baseline、treatment 與差值。它沒有區分研究問題、估計方法、估計結果與證據判定。`claim-audit` 也用固定 `1e-9` 把 `expected_direction: no_change` 解讀為沒有變化。這個規則沒有領域尺度，也沒有處理估計不確定性。

研究依據見 [Experiment comparison 的 estimand 與 equivalence 語意](../research/comparison-semantics.md)。ICH E9(R1) 明確區分 estimand、estimator 與 estimate。ICH E9、FDA 與 EMA 的指引都要求 equivalence margin 預先指定。完整信賴區間必須落在上下 margin 內，才能判定 equivalent。這是跨領域的統計設計原則。它不是臨床法規適用聲明。

## 決定

### Contract 保存 estimand、estimator 與 decision rule

Experiment Contract 新增必要的 `analysis_plan`。它在 lock 前定義以下內容。

- `estimands[]`：穩定 ID、metric、population、conditions、scale、summary measure 與 orientation。
- `estimators[]`：穩定 ID、estimand ref、方法類型、版本、參數與 uncertainty 設定。
- `decision_rules[]`：穩定 ID、estimand ref，以及 `superiority` 或 `equivalence` 規則。

第一版只接受三種 estimator 類型。

- `difference`
- `difference_in_differences`
- `joint_cluster_bootstrap`

程式使用 exhaustive `match`。不建立 estimator registry。新增方法時必須同步修改 schema、實作、測試與文件。

`difference` 的 orientation 固定為 `treatment_minus_baseline`。`difference_in_differences` 必須保存四個具名 cell 與公式方向。`joint_cluster_bootstrap` 必須凍結 resampling unit、strata、replicates、seed、confidence level、interval method 及 method reference。

Decision rule 只能使用 `null_value` 或 `equivalence_margin`。Equivalence rule 必須保存上下 margin、scale、interval confidence level、interval method 與邊界是否包含。Margin、scale 與 interval 規則都進 locked Contract 的 hash。

### Comparison 保存 estimate 與 decision

Comparison Result 新增必要的 `estimates[]`。每筆 estimate 保存以下內容。

- `estimand_id` 與 `estimator_id`
- `point_estimate`
- `interval`
- `sample_size`
- `method_ref`
- `component_estimates`
- `decision`

Decision 結論固定為 `superior`、`inferior`、`equivalent` 或 `inconclusive`。數值方向與證據結論分開保存。Point estimate 大於 null value 不代表 superior。區間跨越決策邊界時只能判 inconclusive。

Equivalence 只在完整 interval 落入預先凍結的上下 margin 時成立。缺 interval、scale 不同、confidence level 不同、interval method 不同或 estimator 不對齊時，都判 inconclusive 並保存 reason code。不得用 point estimate、`p > alpha` 或固定 epsilon 取代 interval 規則。

`metrics` 繼續保存兩個 run 的原始描述值。衍生的 difference、DiD 與 bootstrap estimate 只放在 `estimates[]`。不得把 comparison-level estimand 偽裝成 run metric。

### Claim 分開數值方向與證據結論

Claim 以 `estimand_id` 引用持久化 estimate。`expected_direction` 只接受 `increase` 或 `decrease`，並只核對 point estimate 相對 null value 的符號。Claim 另以 `expected_conclusion` 宣告 `superior`、`inferior`、`equivalent` 或 `inconclusive`。

`claim-audit` 必須從 comparison 的持久化 estimate 讀取 point estimate、interval 與 decision。它不得在 audit 時重新估計，也不得使用固定 `1e-9` 判 `no_change`。Viewer 同樣只渲染持久化結果，不在 Vue 重新計算統計結論。

### Joint cluster bootstrap 採下游 golden 行為

上游移植下游已實跑的 joint cluster bootstrap。每個 replicate 只抽一次 cluster index。所有 component 與最終 contrast 使用同一組抽樣。這保留 component 間的 bootstrap dependence。

Golden test 使用相同輸入、seed 與 replicates，要求上游與下游專案端實作的 point estimate、interval 與 component intervals 完全相同。上游合併並投影後，刪除下游 vendored workaround 與對應 `EXCEPTION:`。

## 拒絕的方案

### 保留 `expected_direction: no_change`

拒絕。它沒有尺度與不確定性語意。把固定 epsilon 當作「沒有變化」會隨 metric 單位改變結果。

### 把 decision 寫回 metric

拒絕。Metric 是量測定義。Decision 是凍結規則對 estimate 的輸出。兩者生命週期不同。

### 導入 estimator plugin registry

拒絕。第一版只有三種方法。Registry 會增加載入、版本與信任邊界，沒有目前需求。

## 後果

- 現有 Contract、Claim、Comparison fixtures 必須遷移。沒有舊 schema fallback。
- `compare-runs` 會多一個 operation module。它負責估計與判定，不擴充 `ProjectSnapshot`。
- Comparison schema 可表示 difference、DiD 與下游已驗證的 joint cluster bootstrap。
- Claim audit 不再把數值接近零誤認為 equivalence。
- Viewer 可忠實顯示 estimate、interval 與 decision，但不擁有統計語意。
