# compute-gate：不解析自然語言規則，翻譯責任留給呼叫者

Phase C 最後一項。L0-L5 的分級概念在 `profiles/experimental/AGENTS.md` 已經定義過，這裡是把「能不能升級」變成機械可判定，同時確立一條邊界：**Contract 裡的 `scale_up_rule`／`abort_rule` 是自然語言，這支工具不自動解析它。**

## 為什麼不解析自然語言規則

考慮過用 LLM 讀 `scale_up_rule`（例如「pilot recall 提升 > 3pp 才跑 full」）自動抽取出 metric／comparator／threshold。沒這麼做：這樣一來「規則寫的是什麼」跟「規則有沒有被滿足」兩個判斷都混進同一次不可重現的推論，這正是 experiment-lint／compare-runs／claim-audit 一路建立的原則要避免的事——能機械判定的部分要跟語意判斷分開，而「這句自然語言等於哪組參數」本身就是一次語意判斷，不該讓它悄悄躲進一支號稱確定性的腳本裡。

改成：呼叫 `compute_gate.py` 的人（agent 或使用者）自己把 `scale_up_rule` 翻成 `--scaleup-metric`／`--scaleup-comparator`／`--scaleup-threshold` 這組參數，翻譯這一步是明確、可審查的（就寫在呼叫的指令裡），之後拿這組參數去對實際數字，才是真正機械、可重複的部分。跟 claim-audit 的 `expected_direction` 是同一個設計精神：語意翻譯跟數字核對分兩段，不要合成一段。

## 序列化升級，不准跳級

`gate-state.json` 記录目前在哪一級、升降級的完整歷史（append-only，跟 run 一樣不覆寫）。`compute_gate.py` 硬性要求 `current_level` 的下一級一定是申請的那一級，跳級直接拒絕（exit code 2），沒有「這次特殊情況跳過 pilot」的後門——這是使用者原始規則 12「昂貴的實驗不是預設權利」的直接體現。

失敗（`failed`）跟中止（`aborted`）刻意分開：`failed` 代表這次帶的證據不夠，可以補證據後重新申請同一級；`aborted` 代表 `abort_rule` 觸發，這條路線視為終止，不是繼續重試的狀態。混在一起會讓人以為 abort 之後還能像 failed 一樣「補證據重來」，但 abort 通常代表方向本身有問題，不是證據不足的問題。

## Pilot 預算檢查只在 L3 生效

Contract 的 `compute_budget.pilot_max_minutes`／`pilot_max_samples` 這兩個欄位早在 Experiment Contract schema 就有了（Phase B），但一直沒有東西真的去檢查。這輪接上：只在申請 `L3`（小規模試跑）且同時提供 `--contract`／`--pilot-run` 時比對實際耗時，其餘等級不套用這個欄位——欄位名稱本身就是 `pilot_max_minutes`，語意上只該管 pilot 這一級。

## 6 個情境全部機械驗證

合法序列升級、跳級被擋、`abort_rule` 觸發、`scale_up_rule` 不足、補證據後 `scale_up_rule` 通過、pilot 預算超支——六種都用 `compute_gate.py` 實際執行過，exit code 與 `gate-state.json` 的 `current_level`／`history` 都符合預期，不是憑空宣稱。跟 claim-audit 不同，這六個情境全部是機械可判定的，沒有語意段需要另外走一遍——`compute-gate` 本身不含語意判斷，語意判斷（規則翻譯）已經被推到呼叫端了。

## Consequences

- Phase C 到這裡告一段落：`Experiment Contract → experiment-lint → Run → compare-runs → claim-audit`，加上橫向的 `compute-gate` 管制升級節奏，六個 skill 都是確定性優先、語意判斷有明確邊界。
- UI／viewer 現在有四份輸出 schema 可以消費（`comparison-result`、`claim-audit-result`、`gate-state`，加上 `run-envelope`），但這輪還是不碰——契約要再穩定一段時間。
- `pilot-planning`（借 `phd-skills/launch` 的執行前檢查清單）還沒做，留待真的有人在這個流程上重複手動檢查、覺得痛了再說，依 Institutionalize Repeated Failures 升格。
