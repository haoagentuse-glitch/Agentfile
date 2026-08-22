# ProjectSnapshot 深 module 與 operation-scoped validation

`experiment_records` 原本每個檢查各自開檔、各自 glob、各自解析 JSON。`_validate_review_policy` 自己讀 `definitions/<id>.json`，`_evidence_experiment_id` 自己掃 `claims/*.json`，`review_package` 再掃一次 `runs/*.json`。同一份紀錄在一次執行裡被讀好幾遍，而「這份紀錄屬於哪個 experiment」這個判斷散在三個地方。

同時 `transition` 在建立事件前跑全專案驗證。任一筆紀錄有錯就拒絕建立事件，即使那筆紀錄跟這次轉移的 experiment 毫無關係。

## 決定

新增一個 module：`load_project(root) -> ProjectSnapshot`。它是紀錄層的唯一入口。

`ProjectSnapshot` 負責六件事，不多也不少：

1. 載入 `records/experiments/` 底下的全部紀錄，一次。
2. record ID index：由 `(類型, ID)` 取得紀錄。ID 依類型而定，`definitions` 用 `experiment_id`，`metrics` 用 `name`，其餘類推。
3. 跨 record reference：claim 指向哪個 experiment、audit 屬於哪個 claim、Contract 引用哪些 metric 定義。
4. dependency closure：一個 experiment 的全部相關紀錄。
5. RFC 8785 contract hash：Contract 的正規雜湊。
6. 共用資格檢查：一份稽核適不適用語意審核與 reviewer policy。

`ProjectSnapshot` 不含比較演算法、不含 Compute Gate、不含生命週期狀態機。這三者各自有擁有者（`compare_runs`、`compute_gate`、`lifecycle-state.schema.json` 的轉移表），不搬進來。理由是它們回答的是「這些數字代表什麼」，而 `ProjectSnapshot` 只回答「有哪些紀錄，它們怎麼互指」。兩種問題混在一起，檢索結果就會悄悄變成決策依據。

## Operation-scoped validation

`validate` 的範圍不變：全專案。使用者問的就是「這個專案現在合不合規」。

`transition` 改為只驗證目標 experiment 的 closure。跟這次轉移無關的 experiment 有錯誤，不得阻塞這次轉移。

兩者用同一組檢查函式，只有輸入的紀錄集合不同。差別是範圍，不是嚴格度——同一筆紀錄在兩條路徑上得到同一個判定。

候選事件本身的檢查不受 closure 影響。`transition` 仍然逐一解析 `--evidence-ref`，仍然拒絕引用別的 experiment 的證據。closure 縮小的是「既有專案狀態」的檢查範圍，不是候選事件的檢查範圍。

無法歸屬到任何 experiment 的紀錄（JSON 壞掉、類型不明、缺 `experiment_id`）不進任何 closure。`validate` 會報告它們，`transition` 不會被它們擋住。

## Contract hash 用 RFC 8785，不用 `json.dumps` 的參數組合

`contract_hash` 這個欄位宣告在 schema 裡，`experiment-design` 技能要求算它，但整包工具既不算也不驗。宣告了卻沒有工具讀的欄位，等於沒有機械執行力。

序列化形式也必須訂死。鍵序、非 ASCII 轉義、分隔符空白，三者任一不同就算出不同的雜湊。用 `json.dumps(sort_keys=True, ensure_ascii=False, separators=(",", ":"))` 可以得到一個穩定結果，但那是本專案自己發明的一種形式，跟別的專案算出來的雜湊不可比。

改用 RFC 8785 JSON Canonicalization Scheme：

- 移除頂層 `contract_hash` 欄位本身，其餘欄位全部保留。
- 依 RFC 8785 正規化：鍵以 UTF-16 code unit 排序，數字用 ECMAScript 的最短往返表示，字串只轉義 JSON 規定的字元，不加空白。
- 對 UTF-8 bytes 算 SHA-256，輸出小寫 64 位 hex。

雜湊值不帶 `sha256:` 前綴。演算法由這份 ADR 與 schema 的 pattern 固定，不由資料自述。

`status` 為 `locked` 的 Contract 必須有有效的 `contract_hash`。lock 是開始花算力的那一刻，此後這份檔案不得再改；沒有雜湊的 lock 只是一句宣稱。

新增子命令：

```bash
python -m experiment_records contract-hash <definition>
```

預設只驗證，印出 expected 與 actual，不改檔。`--write` 只改 `contract_hash` 這一個欄位，並列出 old 與 new。

不保留舊格式 fallback。帶 `sha256:` 前綴或其他形式的舊值一律判為無效，重算即可。同時接受兩種格式，等於沒有正規形式。

## Contract 引用的 metric 必須解析得到定義

`primary_metric` 與 `secondary_metrics` 是字串。原本沒有任何檢查確認它們對應到 `records/experiments/metrics/` 裡真實存在的定義。一份 Contract 可以引用一個不存在的指標而通過驗證，直到執行時才發現。

改為：兩者都必須解析到一份 metric definition 紀錄，比對的是該紀錄的 `name`。這一項是機械可檢的，不需要語意判斷。

## 機械檢查沒過時，語意審核與 reviewer policy 為不適用

`mechanical_pass` 為 `false` 時，工具自己就會印「不需要再判斷 scope」。但 `_validate_review_policy` 對每一份稽核都套用政策檢查，於是同一個工具一邊說不必審，一邊要求提供獨立審核者的身分。

沒有誠實的填法能通過：填 `second_model` 是假的，填 `same_context` 撞上政策不滿足，只填 `independent: false` 撞上缺 `reviewer_kind`。刪掉那份稽核可以讓錯誤歸零，但那等於把「第一次寫錯了」從紀錄裡抹掉。

改為：`mechanical_pass` 為 `false` 時，`review_independence` 與 `reviewer_kind` 不再是必填，reviewer policy 不套用，稽核者與產出者相同也不再要求宣告獨立性。

「不適用」與「缺漏」在紀錄上因此分得開。已經填了的欄位仍然要自洽——`reviewer_kind=same_context` 配 `independent: true` 依舊是錯誤，因為那是資料自相矛盾，不是缺漏。

`mechanical_pass` 為 `false` 時 `final_verdict` 不得是 `fully_supported` 或 `partially_supported` 的規則不變。那條檢查判的是結論強度，不是審核者身分。

## 後果

- 紀錄只載入一次，跨檔判斷有單一來源。新增跨 record 檢查時不必再寫一次 glob。
- 誠實記錄下來的機械失敗，不再產生無法修復的驗證錯誤，也不再擴散到不相干的實驗。
- Contract 的凍結從一句規範文字變成機械執行力。`contract_hash` 對不上就是錯誤，換一台機器也算得出同一個值。
- 下游專案原本自建的 `contract-hash` 子命令與 `validation.py` 的 `EXCEPTION` 補丁可以移除，改用上游版本。序列化形式改為 RFC 8785，跟下游原本的 `sort_keys=True` 版本算出的雜湊不同，需要重算一次。
