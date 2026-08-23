# 逐筆結果作為 cluster bootstrap 的輸入

[ADR 0018](0018-comparison-estimands-estimates-and-decisions.md) 讓 Contract 可以凍結 `joint_cluster_bootstrap` estimator，comparison 也有位置保存 interval。但 run envelope 只保存彙總後的 metrics，`compare-runs` 拿不到重抽所需的逐筆資料。結果是 Contract 宣告得了、CLI 產不出來，estimand 永遠沒有 estimate。

下游 frus-agentic-rag_v2 為此在 vendored 套件裡新增本地欄位與本地實作，並留了 `EXCEPTION:`。移植估計量本身不足以收回那條例外，輸入路徑也要進上游。

## 決定

### Run envelope 保存逐筆結果的位置

新增兩個選填欄位。

- `per_question_ref`：project-ref，指向 JSONL 檔。
- `per_question_metric`：這份逐筆結果量的是哪個 metric。

JSONL 每列固定四個欄位。

- `case_id`：配對用的題目識別碼。
- `cluster`：重抽單位。
- `component`：這一列所屬的分層，對應 estimator 的 `component_a`／`component_b`。
- `value`：該題的量測值。

欄位名用 `component` 而非 `kind`，跟 `component_a`／`component_b` 與 `component_estimates` 同一套詞彙。同一個概念在紀錄裡只有一個名字。

### 配對規則不補值

`compare-runs` 讀兩個 run 的逐筆結果，以 `case_id` 配對，逐題相減得到差分列。三種情況直接失敗，不補值也不略過。

- 題目集合不一致：少一題就不是配對比較。
- 同一題兩邊的 `cluster` 不同：重抽單位被換過。
- 同一題兩邊的 `component` 不同：分層被換過。

失敗不會中斷整份 comparison。該 estimand 不產生 estimate，原因寫進 `notes`。缺 `per_question_ref`、檔案不存在、路徑跑出 project root，處理方式相同。

### 上游不驗證逐筆結果的內容

Validator 不檢查 JSONL 的列數、值域，也不檢查 `per_question_metric` 是否對得上 metric 定義——現行 run envelope 的 `metrics` 與 `metric_definitions` 同樣沒有這層檢查。只在這個欄位加檢查會造成同一份 record 裡兩套不同強度的規則。

## 拒絕的方案

### 讓 compare-runs 接受 `kind` 或 `component` 兩種欄位名

拒絕。相容層會讓同一個概念在紀錄裡有兩個名字，之後每個讀取端都要處理兩種寫法。下游改欄位名是一次性的機械改寫。

### 把逐筆結果直接放進 run envelope

拒絕。逐筆結果是千列等級的資料，放進 record 會讓每次讀 run 都付出這個成本，也會讓 `contract_hash` 以外的 record 大小失控。JSONL 留在 artifact 層，record 只保存指標。

### 由命令列給重抽參數

拒絕。replicates、seed、confidence level 與 interval method 都在 Contract 的 `analysis_plan` 裡凍結。同一組紀錄重跑必須得到同一個判定。

## 後果

- Contract 凍結 `joint_cluster_bootstrap` 之後，`compare-runs` 產得出 point estimate、interval、component estimates 與 decision。
- 下游可刪掉本地的 `contrasts.py` 與 run envelope 的本地欄位，連同對應的 `EXCEPTION:`。
- 下游既有的逐筆結果檔要把 `kind` 改名為 `component`。這是機械改寫，值不變。
