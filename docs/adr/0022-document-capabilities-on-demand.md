# 文件治理吸收 claude-Godzilla-z 的能力，不吸收它的預設產物

`claude-Godzilla-z` 有一套 18 份的文件模板庫（`VibeCoding_Workflow_Templates/00–17`）與四個上層治理機制（`ABLATION.md`、`.out-of-scope/`、`PLAYBOOK.md` 的 A/B/C 工作深度、`01` 的文件路由）。它自己說得很清楚：這 18 份是能力庫，不是待辦清單。

逐項比對本包現況之後，多數項目的結論是**已經有擁有者**。真正的缺口只有一個，而且不在文件層：本包替自己寫的規則沒有地方放——根 `AGENTS.md` 逐位元等於 `core/AGENTS.md` 加上 `profiles/software/AGENTS.md`，所以任何「怎麼維護 agentfile」的條文都會投影進每個下游專案。

核心判準沿用本包既有的門檻：說不出這份文件現在會替誰省下一次溝通、擋掉哪種錯誤、或當哪個流程的真相源，就不要建立它。

## 決定

### 文件是按需能力，不是預設產物

`apply.sh` 不新增任何文件投影。套用本包之後預設產生的文件數維持不變。每種文件的啟用條件由既有擁有者定義，不另設路由層：`docs/PROJECT.md` 與 `docs/architecture.md` 見 `project-docs`，ADR 三條件見 `domain-modeling` 的 `ADR-FORMAT.md`，`openapi.yaml` 見軟體 profile 的「契約驅動」。

### 拒絕紀錄的唯一擁有者是 `docs/adr/`

`ADR-FORMAT.md` 已經寫了兩條相關規則：「明確寫下的『不做』跟『要做』一樣有價值」，以及「被否決的選項，當否決的理由不明顯時……否則半年後又會有人提議 GraphQL」。[ADR 0013](0013-frontier-research-agent-methodology-evaluation.md) 已經在跑 `## 被拒絕的方案` 加 `## 預登記的改判條件` 這個形狀。

要吸收的是**行為**而不是檔案：提出一個曾經研究過的方案之前，先搜既有 ADR 的拒絕段，找到就檢查重啟條件；條件沒變就不重新研究。

### 規則回收寫成 policy，不建帳本

只找到一個過期實例（`zh-lint` 的兩處「這包沒有 CI」，而 `.github/workflows/ci.yml` 已存在）。一個實例不滿足本包自己的升格門檻。因此只寫下方法論與補丁的分類、以及「原始失敗條件不再重現就刪除」的對稱判準，不建立六欄帳本。

### 只治理本包的規則落在根 `AGENTS.md` 的受管前綴之外

`install_prefix` 的 `prefix` 模式本來就允許受管前綴之後接專案特化段，本包的 `.gitignore` 已經在用它承載 Viewer release 副本兩行。`AGENTS.md` 沿用同一個機制，不新增第三份 fragment、不新增 `CONTRIBUTING.md`、不新增 `docs/maintenance/`。這個落點是唯一一個 agent 會自動讀到的。

配套加一條測試，確保根 `AGENTS.md` 的受管前綴等於組裝結果。比對用前綴而非全等——全等會比 `install_prefix` 本身更嚴，且會禁止本包擁有每個下游都被允許擁有的東西。

## 拒絕的方案

### 建立 `docs/rejected/` 拒絕方案登錄

本包已經有三個地方回答「我們刻意不做什麼」：`docs/adr/` 的拒絕段、`wontfix` 標籤的 Issue、`DECISIONS.md` 的「什麼會推翻它」。第四個家會直接違反「同一事實只有一個擁有者」，且 `rule-check` 的 SSoT 那組會在引入它的 PR 上判它重複。

**重啟條件：** ADR 數量成長到用 `rg` 搜拒絕段已經找不全，且實際發生過重複研究同一方案。屆時的正解是從 ADR **自動產生**索引，來源仍然只能是 ADR。

### 建立 `docs/rule-ledger.md` 六欄規則帳本

常駐面是 `AGENTS.md` 128 行加 21 份技能的 `description`。逐行分類方法論與補丁約六十列，對一個只有三個 commit 歷史的檔案而言是蔓生，而且帳本自己也會過期。為單一案例建制度，正是這個機制要防的事。

**重啟條件：** 出現第三個以上的過期規則實例，或一次模型大版本更新後有大量補丁待重驗。

### 新增 `document-router` 技能

技能是按需載入的，所以 agent 必須先知道「我該載入 document-router」才會知道現在該產生什麼文件——這是 bootstrap 問題。而且它要替 `CONTEXT.md`、`docs/adr/`、`openapi.yaml` 講啟用條件，但那三份的規則已經有別的擁有者，會變成第二份真相源。一張列滿文件類型的表也會被由上往下讀，正是要避免的 waterfall。

**重啟條件：** 啟用條件散在多個擁有者導致實際判錯，且重複發生。

### 把 `00` 的 FR/NFR 問題清單接進 `grilling`

`grilling` 是 vendored 技能，「規則的數量與強度不得增減」。加一份 22 類的 NFR 清單就是增加規則數量。而且它的前緣機制已經由結構保證「沒有任何東西被默默假設掉」——漏掉的 NFR 就是一條沒走過的分支。清單會把前緣紀律換成填表。

**重啟條件：** 出現兩份以上的 spec 或 ticket，其效能、可用性、安全或維運限制是在實作之後才發現的。

### 搬 `12` 與 `17` 的前端架構與資訊架構、`13` 的 production readiness、`14` 的部署與 runbook

零重複失敗證據。本包與現有下游都沒有 production 系統，也沒有需要治理的前端工程。

**重啟條件：** 本包或某個下游真的開始部署並對外提供服務；或某個下游的前端成長到有多頁導航與資訊階層。

### 搬 Godzilla 的 8 個 Agent 結構

Agent 的正當存在理由只有 context 隔離、權限隔離、平行、獨立第二意見。本包目前用技能、獨立 context、git worktree 與 `code-review` 的雙軸 sub-agent 已能處理，且 `code-review` 已經在用平行 sub-agent。帶 persona 的 Agent 若只是重述技能裡已有的領域知識，就是複製。

**重啟條件：** 出現具體且反覆的失敗，是現有機制在隔離或平行上做不到的。

### 依工具分檔規則（`.claude/rules/` 與 `.codex/rules/`）

canonical `AGENTS.md` 由 Claude Code 與 Codex 共讀是本包的核心優勢。除非某條規則確實只有特定 runtime 讀得懂，SSoT 必須留在 canonical source。

**重啟條件：** 出現一條規則，兩個 runtime 對它的解讀確實不同且無法用同一段文字表達。

### 搬整份 `PLAYBOOK.md`

本包已有技能、`to-spec`、`to-tickets`、`tdd`、`implement`、`code-review`、`handoff` 與 experimental 工作流。整份搬會建立第二套完整開發生命週期。只吸收 A/B/C 工作深度分類，且它屬軟體任務路由，落在軟體 profile 而非 `core`——experimental 有自己的生命週期，混進 core 會互相干擾。

### 逐項模板：已有擁有者的部分

| 模板 | 已有的擁有者 | 重啟條件 |
|---|---|---|
| 02 PRD | issue 本身就是 spec；`project-docs` 明文禁止把 feature spec 抄進 `docs/` | feature 範圍需要跨人跨階段固定，且 issue 撐不住 |
| 03 BDD | `to-tickets` 的驗收條件 checkbox；`tdd` 的 seam 紀律與同義反覆禁令 | 出現真的適合 Gherkin 的專案，且有人維護 `.feature` |
| 04 ADR | `ADR-FORMAT.md` 的三條件閘，逐字相同 | —— |
| 05 架構 | `project-docs` 擁有 `architecture.md`；`diagram-design` 擁有圖 | —— |
| 06 API | 軟體 profile 的「契約驅動」，`openapi.yaml` 唯一來源 | —— |
| 07 模組規格 | `codebase-design` 加型別加測試 | 型別與測試已說不清某個模組的領域行為 |
| 08 專案結構 | Structure Follows Need；`rule-check` 的結構那組 | 光看目錄已看不出各資料夾責任與依賴方向 |
| 09 依賴 | 真實依賴圖屬機械產物，[ADR 0004](0004-graphify-optional-structural-layer.md) 已寫死 Graphify 的啟用門檻 | 見該 ADR |
| 10 類別關係 | `diagram-design` 擁有圖；`domain-modeling` 擁有模型 | 領域物件複雜到讀 code 建不起心智模型 |
| 11 Code Review | `code-review` 的雙軸；`rule-check` 的安全、可逆與 SSoT 那幾組 | —— |
| 15 文件治理 | 本 ADR 與軟體 profile 的啟用條件 | —— |
| 16 WBS | `to-tickets` 的垂直切片、阻塞邊與 expand→migrate→contract；GitHub Issues 是唯一任務來源 | 需要對外承諾時程時，優先用 GitHub milestone |

## 後果

- 本次新增技能 0 個、新增預設文件 0 個、`apply.sh` 不改。
- `STATE.md` 移除。它零引用、不投影、寫下後四小時五十六分即與 issue #38、#39 矛盾，是不可重建的衍生視圖。進度由 GitHub Issues 與 git history 回答。
- 根 `AGENTS.md` 取得受管前綴之外的維護段，並由測試守住前綴。四個手動組裝產物裡，`AGENTS.md` 是第一個有測試的。
- 投影連結守衛從兩條路徑的黑名單改為「`apply.sh` 沒投影出去的 `docs/` 路徑一律禁止本機連結」。原版每新增一份上游專屬文件就再開一次同樣的洞。
- 重複提案的成本仍然存在：要靠人或 agent 主動搜 ADR 的拒絕段。這是刻意接受的代價，換掉一個第四擁有者。
