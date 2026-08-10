# claim-audit：機械與語意分工，不是全自動也不是全交給 LLM

Phase C 第二個 skill，接上 `compare-runs` 的輸出，封完 `Experiment Contract → Run → compare-runs → claim-audit` 這條鏈。

## 為什麼要分兩段

「claim 有沒有引用真的存在、沒有 confounded 的比較，數字方向對不對」是可以機械判定的——同一個 claim 跑兩次要給一樣的答案，這種事不該交給 LLM 自由心證（跟 experiment-lint、compare-runs 一路下來的原則一致）。但「這個結論有沒有超出證據涵蓋的範圍」沒辦法寫成規則——「僅限這個資料集」跟「一般都適用」之間的界線，需要理解語言，機械檢查做不到，勉強寫規則只會變成一堆脆弱的關鍵字比對。

所以 `claim_audit.py` 只做機械段，機械段沒過就直接判定（`unauditable`／`unsupported`），機械段過了則把 `scope_verdict` 留成 `pending`，交給呼叫的 agent 讀 `claim-audit` 技能的判準完成語意段，把結果寫回同一份 audit result。這不是偷工，是刻意的分工邊界。

## Claim schema 刻意留小

`claim.schema.json` 只有 8 個欄位：`claim_id`、`statement`（人讀）、`experiment_id`、`comparison_ref`、`metric`、`expected_direction`、選填的 `stated_magnitude`／`magnitude_type`、`scope`。沒有仿 ARA 論文的完整知識圖譜（claim 之間的關聯、多層證據鏈、嚴謹度分數之類）——目前只需要「一個 claim 對一個 comparison 的一個 metric」這條最短路徑，多的東西留到真的需要再加。

`expected_direction` 刻意設計成 `increase`／`decrease`／`no_change`，對應的是**原始數值**該往哪個方向動，不是「有沒有變好」。「變好」需要知道 metric 的 `direction`（higher/lower_is_better），那是語意層的事；機械段只驗證「數字真的照 claim 講的方向動了沒有」，兩件事分開，claim 的 `statement` 本身要不要用「改善」這種字眼是作者的責任，不是 script 幫忙判斷的。

## 判定邏輯

`reference_exists` → `comparison_valid`（false 就是規則 10 的硬限制，直接 `unsupported`，不用往下看）→ `metric_exists`（該 metric 有沒有被 compare-runs 算出來）→ `direction_matches`／`magnitude_matches`（幅度容許 ±10% 相對誤差，數字不可能剛好對到小數點後幾位）。全部過，`mechanical_pass = true`，`scope_verdict` 留 `pending`。任一沒過，`final_verdict` 直接定案，不進語意段。

## 用了 7 個情境驗證，5 個機械、2 個語意——誠實區分

前 5 個（完全受支持、引用 confounded、數值寫錯、方向寫反、引用不存在的 run）全部靠 `claim_audit.py` 實際執行驗證，exit code 跟 `final_verdict` 都對。後 2 個（局部結果被擴張成一般性結論、證據只足以部分支持）**沒辦法用腳本測**——它們測的正是語意段本身，所以驗證方式是照 `claim-audit` 技能的判準，作為呼叫這個技能的 agent 實際走一遍分類，寫進 `scope_reasoning` 解釋依據，不是隨口下判定。這兩種驗證方式不能混為一談，機械測的是「程式邏輯對不對」，語意測的是「給定判準，實際套用會不會得出一致、可解釋的結果」，後者不是自動化測試能取代的。

## Consequences

- `compute-gate` 是唯一剩下的 Phase C 項目，留到下一輪，屆時要另外定 L0-L5 的升級／中止／算力預算規則。
- UI／viewer 現在有三個輸出 schema 可以消費（`comparison-result`、`claim-audit-result`，加上更早的 `run-envelope`），但契約還沒穩定夠久，這輪依然不碰 UI。
