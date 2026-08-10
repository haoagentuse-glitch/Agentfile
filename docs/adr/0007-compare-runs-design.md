# compare-runs：確定性可比較性判定，Run Envelope 補兩個欄位

Phase C 第一個 skill。目的是把 Comparability Guard（見 profiles/experimental/AGENTS.md）從「人工檢查」變成「機械可重複執行的檢查」，同時不重造 phd-skills/compare 已經驗證過的規則。

## 為什麼要擴充 Run Envelope schema

`compare_runs.py` 要逐欄位比對兩個 run 的實際設定，但原本的 `run-envelope.schema.json` 只有 `config_hash`（一個雜湊值），沒辦法從 hash 反推是哪個欄位不同。加了兩個選填欄位：

- `config_ref`：指向這次 run 實際用的設定檔，讓 compare-runs 能載入內容逐欄位比對，而不是只能說「有差異但不知道差在哪」。
- `metric_definitions`：記錄每個 metric 這次是用哪一版定義算出來的，讓 compare-runs 能抓出「兩個 run 的『recall_at_k』其實用不同算法算的」這種情況——這正是使用者要求的「指標定義與 schema 版本」檢查。

兩個欄位都選填，不影響已經寫好的舊 run 資料；沒填的話 compare-runs 會明講「無法逐欄位比對」而不是假裝能比。

## 可比較性怎麼判定：借規則，不借流程

讀過 phd-skills/compare 全文（ADR 0006 已經記過），借了兩條規則的精神：

- **同一 epoch 對齊**的精神延伸成「先確認可比較，才計算差異」——不比較訓練到一半的 run 跟跑完的 baseline，我們的版本是「先過可比較性檢查，任何一項沒過就整體視為不可信」。
- **代理指標跟下游指標分開報**的精神延伸成「指標定義不一致就那個指標單獨跳過，不連坐拖累其他指標」——`latency_ms` 定義一致就正常算，`recall_at_k` 定義不一致就只跳過它自己。

不借的：phd-skills/compare 會自動偵測 wandb／neptune／tensorboard／mlflow 這幾種追蹤工具並直接呼叫它們的 API 拉資料。我們沒有這層——`config_ref`／`metric_definitions` 是使用者自己在寫 Run Envelope 時填的純檔案路徑，不接外部追蹤工具，符合這包目前「records/ 是唯一來源，不強制接 MLflow」的立場（見 ADR 0006）。

## 判定邏輯

固定當作「一定要一致」的維度：`dataset`／`evaluation_set`／`model`（不管有沒有寫進 Contract 的 `controlled_variables` 都會檢查，因為這幾樣不一致的比較幾乎必然沒有意義）＋ Contract 裡宣告的 `controlled_variables`。唯一允許不同的是 Contract 宣告的 `treatment.variable`。除此之外，任何欄位有差異都算「未預期差異」。

三種情況都會讓 `confounded: true`、`comparison_valid: false`：
1. 應該一致的維度實際不同（控制變因漂移）
2. 有未宣告的差異
3. 宣告的實驗變因實際上兩邊相同（沒有處理效應可歸因，即使沒有任何 confound，這種比較本身也沒有意義）

變因混雜時不計算任何指標差異，也不輸出「A 優於 B」這類語句——這是使用者原話的硬性要求，直接反映在 exit code（1 = confounded）跟輸出 JSON 的 `comparison_valid` 欄位上，不是只在文字說明裡提醒。

## 用了 6 個情境實測，不是憑空宣稱

合法單一變因比較、未宣告的預算差異、指標定義不一致、資料集不一致、宣告變因與實際不符、兩個 run 沒有有效變因差異——六種都建了真實的 Contract + config + Run Envelope 跑過 `compare_runs.py`，行為與 exit code 都符合預期，過程記在這輪的 commit 裡。

## Consequences

- `claim-audit`（下一輪）可以直接讀 `comparison-result.schema.json` 的輸出，不用重新解析兩份 Run Envelope。
- UI／viewer 要等 compare-runs 的輸出契約穩定一段時間、真的有更多情境驗證過再開始接，這輪不做。
- `compute-gate` 也留到下一輪；這輪只確立「兩個 run → 可比較性判定 → 指標差異」這條確定性鏈。
