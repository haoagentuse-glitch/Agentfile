# AGENTS.md

唯一規範來源。CLAUDE.md 僅以一行引用本檔。專案特化章節只追加於末尾，不改寫上游條文。

## 核心原則

- **KISS / YAGNI**：禁推測性抽象、設定與過度間接轉介。
- **Context Budget**：AGENTS.md、skills、docs、memory、（未來可能的）graph 一律按需揭露，不預載。本檔只放不變量與導航；機制細節、已知限制留給各自的擁有文件，不重述。
- **Optimize for Comprehension**：降低理解成本優先於降低操作成本。
  - 順向：公開入口到實際邏輯 ≤ 2 跳，不需追 registry／factory／dispatcher。僅轉呼叫的層直接折疊，禁 wrapper chain。第三方庫不計跳數。
  - 逆向（Glass Box）：任何結果可回溯至命令、設定、輸入與 commit。入口預設輸出這四項摘要，不得只回 `Done.`；禁未述副作用。完成與否以 test/lint/build/contract 等實際證據為準，不採自述完成。
- **Walking Skeleton**：先端到端最小可運行版本，新能力疊在已可運作的產品上；不為未完成的複雜度犧牲可運作狀態。
- **Structure Follows Need**：結構隨實際需求生長。無空目錄、無單路徑巢狀、無預建技術分層。模組邊界依「會一起改變的理由」切，不依技術類型切。
- **One Obvious Way**：每種操作單一公開入口，並依「執行面」規範的入口交付——具體入口依 active profile 定義。
- **Single Source of Truth**：依賴、設定、schema、文件各有唯一來源，其餘以連結引用。衍生產物（索引、快取、摘要、generated models、graph）永遠可刪除重建，不得凌駕權威來源。
- **Cheapest Correct Retrieval Primitive**：能用 `rg` 精確比對就不用 embedding；能由程式結構（AST/graph）得到就不讓 LLM 猜；只有語意與歷史問題才查 memsearch。細節見「檢索」一節。
- **Borrow Before Building**：先研究成熟產品與既有依賴的既定解法，不從零發明。沿用順序：既有依賴 → 標準庫 → 成熟函式庫 → 自寫；判準是整體複雜度，非依賴數量。斷言函式庫做不到之前，先查文件與型別。
- **Delete, Don't Deprecate**：過時路徑直接移除，不加相容層、fallback、遷移邏輯。移除對外契約屬難逆決定，依優先序另判。
- **Small Reversible Changes**：一次一事。重構、依賴升級各自獨立成一次變更；變更含清理，殘留即未完成。
- **Parallelism Requires Isolation**：v1 不做協調器。真正開始多 Agent／多帳號平行改同一 repo 時，用 git worktree 隔離，屆時再評估 vendor `using-git-worktrees`；現在不預建。
- **Explicit Over Implicit**：無隱藏依賴、臨時路徑、未述副作用。
- **Measure Before Optimizing**。

## 決策與衝突

優先序：安全與可逆性 > 契約穩定 > SSoT > YAGNI。

- 可逆決定走 YAGNI，取當下最簡。
- 難逆決定（對外契約、資料 schema、持久化格式、儲存選型）依長期考量，不接受「先這樣之後再換」。
- 分不清 → 當難逆處理。
- 新增規則、skill 或工具的門檻：同類失敗反覆發生且有具體證據，才升格為 test／CI gate／AGENTS 規則／skill／工具。「之後可能會用到」不構成理由。

偏離規則不禁止，但須在對應位置留下一行；靜默偏離視為違規。盤點：`rg -n 'EXCEPTION:' --hidden --glob '!.git'`

```
EXCEPTION: <偏離哪條規則 + 理由> | 回收條件: <何時該移除>
```

## 專案結構與依賴

- 專案啟動第一件事是 `git init`，每個改動後自動 commit/push，不必詢問。

語言、框架、依賴管理等技術棧限定規則依 active profile 定義，見本檔末尾追加的 Profile 章節。

## 執行面

約束交付方式，非僅程式碼結構。規範入口依 active profile 定義（見 Profile 章節「執行面」），此處只放跨 profile 都成立的不變量：

**可具名重現**：值得跑第二次的操作都要有名字；名字之外不承載狀態。終端是傳輸層，不是儲存層。

- 尚無名字的操作先加子命令再給指令。「先跑一次看看」不構成例外，診斷同規。不另開腳本檔包裝既有命令。
- 交付格式：每個操作恰好一行可複製指令 + 一句說明。
- 豁免：純環境探查且不重複執行。跑第二次即須落成子命令。

驗收：丟掉 scrollback、換一台機器、clean checkout，能否原樣再做一次？不能 → 缺名字或有環境依賴。

## 輸出

**語言**：對使用者的一切輸出使用中文——回覆、`docs/`、README、commit、issue、本包自有技能檔。

- 有通行中文譯名就用中文；無譯名或翻譯妨礙查找則保留原文（frontmatter、OpenAPI、embedding）。
- 套件、指令、檔名、技術與模型名稱、程式碼識別符一律保留原文。
- vendored 檔案不翻譯。

## 職責邊界

各來源回答的問題不重疊，同一事實只有一個擁有者。

| 來源 | 回答什麼 |
|---|---|
| GitHub Issues | 要做什麼 |
| `docs/` | 系統現在是什麼、為什麼 |
| AGENTS.md | Agent 必須怎麼做 |
| Code / Tests | 系統實際做什麼 |
| memsearch memory | 過去發生過什麼 |
| `CLAUDE.local.md`（Claude Code 原生機制，不進版控） | 這台機器、這個人專屬的規範覆寫 |
| `docs/eval/` | 這包的能力有沒有變好變壞，怎麼量 |

`docs/PROJECT.md` 只記目的、範圍、系統概觀與穩定背景，不是 feature spec 或任務清單，不複製 issue 內容。

判斷專案現況與歷史時的權威順序，**不決定工程行為**：

```text
Code / Tests → Current Docs / ADR → AGENTS.md → Handoff → Conversation Memory → Raw Transcript
```

工程行為始終遵守 AGENTS.md；現況違規是待修偏離，不構成先例。Memory 只解釋歷史，不覆蓋現行 code/docs。Handoff 置於 OS 暫存目錄，不進版控。

## 技能 vendoring

- 每個能力只保留一份實作。外部技能 vendor 進本包，不依賴使用者層級外掛。
- vendored 檔案保留上游內文，只允許注入來源 metadata、將上游 per-repo 設定引用改指向本包設定檔。
- `metadata.source` 記來源 repo 與 commit；授權在頂層 `license` 或 `metadata.license` 擇一宣告，全文放 `LICENSES/`。
- 更新須手動 diff 上游後決定是否採納，不自動同步。

canonical source 為 `core/skills/<name>/` 或 `profiles/<name>/skills/<name>/`；`.claude/skills` 以 symlink 指向投影後的聯集；Codex 直接掃 `.agents/skills`。

## 檢索

三種檢索各司其職，選最便宜、夠精確的那個：

| 工具 | 職責 |
|---|---|
| `rg` | 字面／精確比對 |
| Graphify（deferred，見 [ADR 0004](docs/adr/0004-graphify-optional-structural-layer.md)） | 現行程式碼的結構：symbol、import、call、dependency、影響範圍 |
| memsearch | 語意與歷史：`docs/` 的語意索引、跨 session 記憶 |

Graphify 職責僅限現行程式碼結構，不得碰 conversation memory、Issue、ADR 或 task state——一旦這些邊界混進同一個檢索工具，「檢索結果」會悄悄變成「決策依據」。v1 不安裝，啟用門檻與範圍限制見 ADR 0004。

`docs/` 是唯一來源，語意索引只是可重建快取，指令見 `project-docs` 技能。未安裝或索引失敗不得使主任務失敗，只回報「語意索引未更新」。本包不為索引加 hook 或 watch，不自行改 chunking，不改寫或 vendor 語意工具的官方擷取流程。

跨 session 記憶預設不進版控，細節見 [ADR 0001](docs/adr/0001-memsearch-two-layer-memory.md)、[ADR 0002](docs/adr/0002-memsearch-memory-not-tracked-by-default.md)。記憶與 `docs/` 資料量差距過大時的檢索反轉問題，記在 [architecture.md](docs/architecture.md)，不重述。

Retrieval scope 依 active profile 隔離：`memsearch search` 該不該帶 `--source-prefix records/`，由呼叫的 skill 依自己所屬 profile 決定，見各 skill 的 SKILL.md；`records/` 底下的內容不因為存在，就在不相關的 profile 裡被檢索到。
