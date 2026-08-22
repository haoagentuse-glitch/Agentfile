# Evidence policy 與 Compute Gate 證據輸入

Compute Gate 目前接受 `--run` 做預算及 run-source rule 評估，卻另收 `--run-ids` 寫入 history。兩者可互相矛盾。它也只在 comparison rule 上檢查 `comparison_valid`，沒有一個共用規則回答「這筆 run/comparison/claim 能不能作為這個 gate 的證據」。

Run 的 `stage` 混合了探索、正式執行與重現用途。完成一筆 `diagnostic` 或 `pilot` run 是有效紀錄，但不代表它足以支持正式升級或 claim。反過來，把某個 stage 永久寫死為不合格，也會阻止 Contract 預先定義的特殊證據設計。

研究依據見 [Evidence policy 與 Compute Gate：一手來源研究筆記](../research/evidence-policy-compute-gate.md)。ICH E9 與 FDA guidance 支持預先指定、區分探索與確認用途、控制資料驅動變更及保存可重現評估程序；JSON Schema Draft 2020-12 支持以條件式 schema 封閉不合法的資料組合。這是工程類比，不是臨床法規適用聲明。

## 決定

### Contract 擁有 evidence policy

Experiment Contract 新增 `evidence_policy`，其中 `eligible_run_stages` 是非空、值唯一的 run stage 陣列。它是「哪些 stage 可被正式 evidence 消費」的唯一來源。

新 Contract 的預設政策為：

```json
{
  "evidence_policy": {
    "eligible_run_stages": ["main", "replication"]
  }
}
```

這個預設不把政策藏進 evaluator；Contract 可以在結果產生前明確選擇其他 stage。特別是，不寫死 `diagnostic` 永遠不合格。`diagnostic` 預設不在清單內，但 Contract 可有意納入。

Policy 必須隨 locked Contract 一起凍結並進 contract hash。缺少 policy、陣列為空、stage 不在 run stage enum，或 locked Contract 的 hash 不符，都不能評估為 eligible。

### 一個共用 evidence evaluator

共用 evidence evaluator 是獨立 module，供 comparison、claim audit 與 Compute Gate 使用；不要求 `ProjectSnapshot` 新增 API。它不計算 metric、不決定 promotion threshold，也不改 lifecycle；它只回答一組 runs 是否 eligible，並回傳原因與已解析的 roles。

Evaluator 對每個 run 至少檢查：

- 引用可解析，且屬於目標 experiment；
- `status=completed`，沒有 failure 或 invalid 狀態；
- `stage` 存在於 `evidence_policy.eligible_run_stages`；
- operation 需要 baseline/treatment 時，roles 能由既有 `baseline_run` lineage 唯一解析；
- 需要 comparison 或 claim 時，該紀錄及其 closure 同樣可解析且通過各自的獨立硬條件。

任何必要值缺漏、歧義或不一致，結果都是 ineligible。Evaluator 不用 CLI 順序或檔名推測 role，也不把未知降級成 warning。

### Run role 由 lineage 解析；scope 只屬 Gate rule

Run Envelope 不新增 `role`、`scope` 或 evaluator identity。Comparison 與需要具名 role 的 operation 使用既有 `run_id` 與 `baseline_run` 解析一組 baseline/treatment：baseline 的 `baseline_run` 為 null，treatment 的 `baseline_run` 必須等於該 baseline 的 `run_id`。若兩筆都自稱 baseline、互相指向、ID 重複或有多種解析，均 fail closed。`run_scope=all` 可評估多筆 runs，不強迫把它們壓成單一 baseline/treatment pair；每筆仍須通過共用資格檢查。

Compute Cascade 的 `source: run` rule 新增必要的 `run_scope`，enum 為 `baseline | treatment | all`。它只決定 metric 從哪個已解析 role 讀取；`source: comparison` 不得帶 `run_scope`。Draft 2020-12 conditional schema 拒絕 source、field 與 `run_scope` 的不合法組合。

### comparison、claim 與 gate 分層且 fail closed

三種判定分開保存：

1. `comparison_valid` 只回答結構可比較且未混雜。
2. `evidence_eligible` 回答引用是否符合 Contract policy，且 baseline/treatment role 可唯一解析。
3. claim audit 回答 claim 的機械支持與語意 scope，不重定義前兩者。

不得把 evidence eligibility 併入 `comparison_valid`。一個比較可以在數學與結構上有效，但因使用 pilot stage 而不適合正式 gate；也可能是單一 run-source gate，根本沒有 comparison。把兩者合併會失去失敗原因，也讓不同 operation 無法共用 evaluator。

Compute Gate 的 comparison 或 run source 只要缺少引用、引用不可解析、comparison 無效，或 evidence evaluator 回傳 ineligible，就判 `failed`，不升級。Abort rule 所需 evidence 無法取得時同樣判 `failed`，不得解讀為「未觸發 abort 所以通過」。所有結果在 history 的 checks 記錄原因與實際 refs。

### 移除 `--run-ids`

移除 Compute Gate 的 `--run-ids`。History 的 `run_ids` 只由成功載入、實際接受評估的 `--run` 紀錄之 `run_id` 推導，並保留輸入次序。重複 ID、run 內 ID 與引用不一致，或同一 ID 指向不同內容時 fail closed。

Comparison 與 claim 間接帶入的 runs 由既有紀錄引用解析為 evidence refs，不要求呼叫端再手抄 IDs。沒有舊參數 fallback；這是容易重建的命令列介面，保留兩條來源只會延續矛盾狀態。

## 拒絕的方案

### 寫死 `diagnostic` 不得成為 evidence

拒絕。它符合一般預設，卻把研究用途政策埋進程式。Contract 已有凍結政策的位置；若某個預先設計的 diagnostic run 真是 gate 所需證據，硬編碼會迫使使用者錯標 stage 或繞過 evaluator。

### 把 evidence eligibility 併入 `comparison_valid`

拒絕。`comparison_valid` 的擁有問題是可比較性與 confounding；eligibility 的擁有問題是某個 operation 能否使用該證據。合併會讓同一 comparison 在不同 gate policy 下沒有一致語意，並排除 run-source gate。

### 保留 `--run-ids` 作顯示 metadata

拒絕。顯示 metadata 仍會進 append-only history，讀者會把它當成實際證據。只要可與 `--run` 分離輸入，就無法保證 glass-box traceability。

## 後果

- Evidence 身分從 stage 慣例升格為 locked Contract 的明確政策。
- Comparison validity、evidence eligibility、claim support 保持三個可診斷的判定，不讓一個 boolean 承擔多種語意。
- Comparison、claim audit 與 Compute Gate 對同一 evidence closure 得到同一資格結果。
- 現有 Contract 需要補 evidence policy，run-source rules 需要補 `run_scope`；現有 Compute Gate 呼叫要刪除 `--run-ids`。
- 這份 ADR 只決定契約與 evaluator 邊界；schema、程式與測試由後續實作變更完成。
