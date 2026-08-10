# experimental profile 的三個 skill 借現成的，不從零寫

Phase B 要做 evidence-review、experiment-design、experiment-lint 三個 skill。先研究了三個上游來源，決定各自吸收什麼、跳過什麼，而不是憑空設計。

## fcakyon/phd-skills（MIT，commit `8d642d3`）—— 直接 vendor 兩個，裁一個

讀過 `literature-research`、`experiment-design`、`compare`、`launch` 四份 SKILL.md 全文（非摘要）：

- **`experiment-design` → vendor，最小修改。** 上游的 Step 1-7（釐清假設、單變因隔離、實驗矩陣、資源估算、config stub、執行計畫、分析計畫）加 Verification Checkpoints，內容跟我們的 Experimental Engineering Rules（單變因、metric 凍結先於結果、budget 檢查）幾乎一一對應，比自己設計更成熟。修改只有兩處：輸出從「聊天室裡的表格」改成寫一份 `records/experiments/definitions/<experiment_id>.json`（我們的 Experiment Contract），並在最後串 `experiment-lint`。
- **`literature-research` → vendor 後裁成 `evidence-review`，改動較大。** 上游是為了寫新論文找研究缺口（gap analysis 找沒人做過的方向），跟我們「選一個現成做法之前先看證據」的目的不同。留下 Step 1-2（範圍界定、系統性搜尋：直接搜尋／citation chaining／venue／open source discovery）跟 Citation Integrity 段落（每個引用要可查證、標示不確定的地方）——這兩段直接對上我們要的「證據優先級」跟「UNVERIFIED 標記」。砍掉 Step 3-6（分類表、gap 矩陣、gap 驗證信心分級、BibTeX 產出）——這是找論文缺口的機制，我們不寫論文。輸出格式換成使用者原本定義的 Problem/Candidate A-B-C/Evidence/Selected/Why not/Unknowns/Cheapest experiment。
- **`compare`、`launch` 讀過，這輪不引入，只記筆記給 Phase C。**
  - `compare` 的核心規則「same-epoch alignment」——比較還在訓練中的 run 跟 baseline 時，必須把 baseline 切到 student 當前的 step，不能拿 baseline 的最終值比，這是最常見的比較錯誤來源；還有「proxy metric 跟 downstream metric 分開報，不能只看 proxy 就宣布贏家」。這兩條該收進未來的 `compare-runs` skill。
  - `launch` 的 pre-flight checklist（跟參考 config diff、run 命名規則、path 存在性檢查、監控設定、ETA）跟關機清理順序（本機 checkpoint → 遠端 artifact → tracker run → scheduler 預約，四步驟依序清）——該收進未來的 `pilot-planning`／`compute-gate` skill。
  - 兩者都掛在 phd-skills 自己的 Claude Code Stop hook 上（`reason` 觸發自動路由），這部分不引入——我們不裝 hook，這包的「optional 工具不做成 mandatory lifecycle」原則。

授權：MIT，全文放 `LICENSES/fcakyon-phd-skills-MIT.txt`。

## ARA（Agent-Native Research Artifact，arXiv 2604.24658）—— 只借概念，沒有東西可以 vendor

查過 `Orchestra-Research/Agent-Native-Research-Artifact` 這個 repo：**只有論文跟示意目錄結構，沒有實際的 schema 檔案或程式碼可看**（頁面自己也建議去 `/packages` 或 `/skills` 找實作，但那些不存在）。所以這不是「vendor 一份東西」，是「讀一篇論文借幾個概念」：

- **claim → experiment → evidence 的綁定鏈**：claim 引用 experiment，experiment 引用 evidence，不允許 claim 憑空存在。我們的 run envelope 已經有 `baseline_run`/`treatment` 欄位，這條提醒我們之後如果要加「claim」這層（例如 claim-audit skill，Phase C），要讓 claim 明確指回具體 run，不能只寫「這個方法比較好」這種沒有可回溯依據的斷言。
- **exploration graph 保留 dead-end，不只保留成功的 run**：失敗的實驗、被拒絕的假設，是研究過程本身的一部分，不該被線性敘事丟掉。我們的 run envelope 已經有 `status: invalid` 的概念（AGENTS.md 第七條「跑錯的 run 標記 invalid，不得刪除或覆蓋」），這條確認這個設計方向是對的，不用加新機制。

不採用 ARA 的四層架構（結構化科學邏輯層／可執行程式碼層／探索圖層／證據層）當我們自己的目錄結構——那是給「整篇論文都要 agent 可執行」設計的完整協定，比我們需要的重，我們只要 run envelope + metric schema 就夠。

## Scholar Loop（renee-jia/scholar-loop，MIT）—— 只借 funnel 形狀，不碰它的 orchestrator

confirm 過這個東西的實際行為：Director 提案 N 個想法 → 廉價 smoke screen 並行初篩 → 3 seeds + 統計顯著性的 verify → 5 seeds 的 full → governor 依 `max_cost`/`max_rounds`/`dry_patience`（無進展就停）管控預算。**它確實有停止機制，不是字面上的「永不停止」**，但它是一個會自己決定「還要不要再跑一輪、要不要多花錢」的 autonomous multi-agent loop——這正是使用者原話要避免的「看到改善就自行投入更多算力」的行為模式，不管它有沒有預算上限都不該把這種決策權交給自動化迴圈。

借用的只有 funnel 的**形狀**：smoke（一次，便宜）→ verify（多 seed + 顯著性檢定）→ full（完整 seed 數），這跟使用者原本定義的 Compute Gate L0-L5 分級同構，是三階段的簡化版，驗證了「先便宜篩、貴的留到最後」是站得住腳的既有模式。**不引入它的 Director/Reasoner/Governor 這套自動決策機制**——這包的 Compute Gate 每一級要不要往上升，由人或呼叫的 agent 讀 Contract 裡的 `scale_up_rule` 自己判斷，不自動觸發。

## 結論

三個 skill 的實作依據：

| Skill | 來源 |
|---|---|
| `experiment-design` | vendor `phd-skills/experiment-design`，加輸出 Contract 檔案 + 串 lint |
| `evidence-review` | vendor `phd-skills/literature-research` 的搜尋方法論 + citation integrity，砍掉 gap-analysis 部分，換成 Research Gate 輸出格式 |
| `experiment-lint` | 自寫，deterministic script + JSON Schema，不是 prompt skill——能機械判定的規則（必填欄位、baseline/treatment 是否有未宣告的差異）不交給 LLM 自由判斷，SKILL.md 只負責觸發跟解釋結果 |

`compare-runs`（Phase C）借 `compare` 的 same-epoch alignment 規則；`pilot-planning`／`compute-gate`（Phase C）借 `launch` 的 pre-flight checklist 跟 Scholar Loop 的 smoke→verify→full 形狀。都不是這輪的範圍。
