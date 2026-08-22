# Evidence policy 與 Compute Gate：一手來源研究筆記

研究日期：2026-08-22

## 問題

Compute Gate 應如何區分「可執行的 run」與「可作為升級、比較及 claim 證據的 run」？哪些條件應由資料契約與共用 evaluator 機械執行？

本筆記只借用三份一手來源的設計原則。ICH 與 FDA 文件規範臨床試驗，不直接管轄本專案的軟體實驗；以下對本專案的套用均是工程類比，不是法規符合性宣稱。

## 來源與發現

### ICH E9：探索結果與確認性證據不是同一角色

**VERIFIED** — ICH E9 把 confirmatory trial 定義為受充分控制、假設事先陳述並接受評估的試驗；關鍵假設直接來自主要目標、預先定義，並在完成時檢驗（§2.1.2，PDF pp. 7–8）。相對地，exploratory studies 應有清楚目標，但其彈性目的包括探索資料與形成後續確認性試驗的基礎（§2.1.3，PDF p. 8）。來源：[ICH E9 official PDF](https://database.ich.org/sites/default/files/E9_Guideline.pdf)。

**VERIFIED** — ICH E9 要求 interim analyses 預先規劃並寫入 protocol；偏離計畫可能使結果失效，必要變更應儘早以 amendment 指定，並討論對分析與推論的影響，且整體第一類錯誤率仍須受控（§4.5，PDF pp. 22–23）。來源：[ICH E9 official PDF](https://database.ich.org/sites/default/files/E9_Guideline.pdf)。

**INFERENCE** — 對本專案而言，`diagnostic`、`pilot` 或 `tune` run 可以合法存在並用來找錯、選方向，但不能因為「成功跑完」就自動取得正式 evidence 身分。Evidence eligibility 應由凍結的 policy 指定，而不是由 stage 名稱的隱含直覺決定。

### FDA Adaptive Designs：預先規劃、共用評估程序與可重現 operating characteristics

**VERIFIED** — FDA 將 adaptive design 定義為根據試驗中累積資料，允許對設計作「prospectively planned」修改的臨床試驗設計（§II.A，PDF p. 5）。來源：[FDA Adaptive Designs official guidance](https://www.fda.gov/media/78495/download)。

**VERIFIED** — FDA 指出，依未預先規劃的 comparative interim analyses 更改族群、樣本數、主要 endpoint 或分析方法，會造成第一類錯誤率控制與結果解釋的困難（§VI.H，PDF p. 26）。來源：[FDA Adaptive Designs official guidance](https://www.fda.gov/media/78495/download)。

**VERIFIED** — FDA 要求評估設計的 operating characteristics，典型內容包括第一類錯誤率、power、預期／最小／最大樣本數、效果估計偏誤及信賴區間 coverage；複雜設計可用模擬，且應交代情境、迭代數、結果、軟體、程式碼與 random seeds（§VI.A、§VIII，PDF pp. 21–23、31–32）。來源：[FDA Adaptive Designs official guidance](https://www.fda.gov/media/78495/download)。

**INFERENCE** — Gate 不應各自發明「哪些 run 算證據」或靠命令列順序猜 baseline/treatment。Comparison、claim audit 與 Compute Gate 應共用同一個 eligibility evaluator；run role 由既有 `baseline_run` lineage 唯一解析，rule 再以 `run_scope` 明列要讀哪個 role。

### JSON Schema Draft 2020-12：條件式契約可拒絕不完整組合

**VERIFIED** — Draft 2020-12 的 `if`／`then`／`else` 依條件套用 subschema；`dependentSchemas` 可在物件含某 property 時要求整個 instance 再通過指定 schema（Core §10.2.2）。`unevaluatedProperties` 可對未被相鄰 applicator 評估的 properties 套用 schema，常用於組合 schema 後拒絕額外欄位（Core §11.3）。來源：[JSON Schema Draft 2020-12 Core](https://json-schema.org/draft/2020-12/draft-bhutton-json-schema-01)、[Draft 2020-12 official overview](https://json-schema.org/draft/2020-12)。

**INFERENCE** — `evidence_policy` 與 rule 的 `run_scope` 所需欄位可由 schema 表達成封閉的合法組合。Schema 只能保證單筆資料的形狀；跨 run 的共用 evaluator、experiment 歸屬、stage eligibility、comparison/claim 可用性仍須由獨立的共用 evaluator 檢查。

## 對設計的約束

1. Evidence eligibility 是獨立政策。它不等同 run 成功、不等同兩 run 可比較，也不等同 claim 已受支持。
2. Contract 應以 `evidence_policy.eligible_run_stages` 明列可作正式證據的 stage。預設建議為 `main` 與 `replication`；專案若要納入其他 stage，必須在看到結果前凍結於 Contract。
3. 不把 `diagnostic` 寫死為永遠不合格。診斷 run 的一般角色是探索，但少數預先設計的診斷實驗可能是某個明確 gate 的有效證據；是否合格由 policy 決定。
4. 比較、claim audit 與 Compute Gate 必須呼叫同一個獨立 evidence evaluator。它應檢查 run 狀態、experiment、stage，並由既有 `baseline_run` lineage 唯一解析 baseline/treatment role。
5. Run-source rule 必須以 `run_scope` 明列讀 `baseline`、`treatment` 或 `all`；缺欄位、引用無法解析、role 不唯一或資格不明時一律 fail closed。
6. `comparison_valid` 只回答比較結構與混雜問題。Evidence eligibility 另欄判定，避免一個 boolean 同時承擔「可比較」與「可用於這個決策」兩種問題。
7. Gate history 的 run IDs 應由實際載入並通過 evaluator 的 `--run` 輸入推導。獨立的 `--run-ids` 會允許 history 宣稱一組與實際評估不同的 runs，應移除。

## 限制與改判證據

- **UNVERIFIED** — 這三份來源沒有規定軟體實驗 stage 的名稱或本專案應採用的預設集合；`main`／`replication` 是依本專案既有 stage model 作出的工程決定。
- 若後續出現兩筆以上或非 baseline/treatment lineage 的正式證據集合，應先以實際案例定義 role resolution；在此之前不增加通用 role registry。
- 若 Draft 2020-12 validator 無法一致執行所需的 conditional／unevaluated 語意，應以契約測試證明問題，再調整 schema 形狀；不得靜默降級成接受未知欄位。
