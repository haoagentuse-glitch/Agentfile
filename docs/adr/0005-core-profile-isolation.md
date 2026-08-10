# 拆成 core + profile，不再無差別套用整包

這包原本假設所有專案都是「軟體工程開發」：`skills/`、`AGENTS.md`、`.claude/settings.json` 全部無差別複製到任何目標專案。使用者在做演算法／RAG／ML 這類實驗型工作時發現：一般軟體開發的約束防不住實驗特有的失真模式——baseline 漂移、變因混雜、事後挑指標、budget 不一致。這些需要一整套跟「軟體工程」性質不同的不變量（凍結 baseline、控制變因、決策規則先於結果），但同時大部分現有規則（KISS/YAGNI、SSoT、Glass Box、Context Budget……）對任何技術專案都成立，不該為了加這批新規則就複製一整份新的 AGENTS.md。

決定：拆成 `core/`（永遠啟用的共通能力）+ `profiles/<name>/`（只在被選為 active profile 時才生效的特化規則與 skill）。`apply.sh` 依 `--profile` 參數（預設 `software`）組裝目標專案，未啟用 profile 的規則、skill、設定完全不會出現在目標專案裡——不是「寫在文件裡告誡 agent 不要用」，是實體檔案不存在，agent 讀不到就不可能誤用。

## 機制（不是新發明，是既有慣例正式化）

`AGENTS.md` 開頭本來就寫「專案特化章節只追加於末尾，不改寫上游條文」。這次只是把「upstream」正式定義成 `core/AGENTS.md`，「專案特化章節」正式來源改成 `profiles/<active>/AGENTS.md`，`apply.sh` 組裝時純文字串接成一份實體檔案，交給任何工具（Claude Code、Codex）讀都一樣——**不用 Claude Code 的 `@import` 語法**，那是 Claude 專屬機制，Codex 讀不到，會破壞這包「兩邊讀同一份規則」的核心賣點。

`.claude/settings.json` 用同樣的精神但不同機制：JSON 不能純文字串接，`apply.sh` 用 `jq` 合併 core 跟 profile 各自的 `permissions.allow`／`deny` 陣列。

Skill 跟文件模板走實體檔案聯集：`apply.sh` 對 `core/skills/`、`profiles/<active>/skills/`、`core/.claude/`、`profiles/<active>/.claude/` 依序 `copy_tree`，同一個檔名先到者跳過（core 跟 profile 的檔名理論上不重疊，重疊代表分類錯誤）。

Retrieval scope 用 memsearch 原生的 `search --source-prefix` 隔離，不需要另外接多 collection 的複雜度——查詢該不該帶 `records/` 這個 prefix，由呼叫的 skill 自己知道自己屬於哪個 profile。

## 範圍界定

- `records/conversations/` 刻意不建。對話記憶已經有唯一擁有者（`.memsearch/memory/*.md`，由 memsearch 官方擷取流程決定寫哪），[ADR 0001](0001-memsearch-two-layer-memory.md) 明講不改寫它的官方流程。`records/` 只放這包目前真的沒有擁有者的新記錄類型（`research/`、`experiments/`），conversations 概念仍在，物理位置留在原處。
- Walking Skeleton 分階段：Phase A（本 ADR 記錄的這輪）只做結構搬遷——把現有內容依分類搬進 `core/` 跟 `profiles/software/`，改 `apply.sh` 支援 `--profile`，零新能力，先求跟改動前行為零回歸。`profiles/experimental/` 的實際內容留給下一輪；`apply.sh` 當時對 `--profile experimental` 會明確報「尚未建立」而不是靜默失敗或產生半殘缺的專案。

**Phase B 已完成**（見 [ADR 0006](0006-experimental-profile-upstream-evaluation.md)）：`profiles/experimental/` 現在有 `evidence-review`／`experiment-design`／`experiment-lint` 三個 skill、`records/experiments/` 的三份 schema、`profiles/experimental/AGENTS.md`。`records/` 的 schema 來源實際放在各 profile 自己底下（`profiles/<name>/records/`），部署時才投影成目標專案的頂層 `records/`——這點原本沒有明講，補在這裡：跟 skill／`.claude/` 同一套「來源分層、部署時聯集/投影」的機制，不是新規則。

## Consequences

- 好處：實驗型專案不會被迫背負 Python venv／pytest／OpenAPI 契約這些跟它無關的規則；軟體專案也不會因為要支援實驗場景而背上 baseline／Experiment Contract 這類用不到的概念。兩邊各自的 AGENTS.md 都比「合併版」短，符合 Context Budget。
- 代價：新增一條規則前要先判斷它屬於 core 還是某個 profile，多一步分類成本；跨 profile 共用的東西如果分類判斷錯（該進 core 卻放進某個 profile），會在另一個 profile 悄悄消失而不易發現——這是為什麼 `apply.sh` 對每個 profile 都要能單獨套用、單獨驗證，不能只測預設路徑。
- agentfile 自己套用自己的機制：`.claude/skills`、根目錄 `AGENTS.md`、根目錄 `.gitignore`、根目錄 `.claude/settings.json` 都是手動組裝出跟 `apply.sh --profile software` 相同邏輯的結果（`apply.sh` 本身拒絕以自己為目標，見 [ADR 0003](0003-apply-copies-not-symlinks-to-dotfiles.md)），改動 `core/` 或 `profiles/software/` 底下任何來源檔案後，這四個組裝產物要手動同步重跑組裝，不會自動更新。
