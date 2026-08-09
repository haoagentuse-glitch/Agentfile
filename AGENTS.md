# AGENTS.md

唯一規範來源。CLAUDE.md 僅以一行引用本檔。專案特化章節只追加於末尾，不改寫上游條文。

本檔只放不變量。做法與步驟放技能裡，此處不複述。

## 核心原則

- **KISS / YAGNI**：只做當下所需，選能完全滿足現況的最簡實作。禁推測性抽象、設定與過度間接轉介。
- **Optimize for Comprehension**：降低理解成本優先於降低操作成本。
  - 順向：公開入口到實際邏輯 ≤ 2 跳，不需追 registry／factory／dispatcher。僅轉呼叫的層直接折疊，禁 wrapper chain。第三方庫不計跳數。
  - 逆向（Glass Box）：任何結果可回溯至命令、設定、輸入與 commit。入口預設輸出這四項摘要，不得只回 `Done.`；禁未述副作用。
- **Walking Skeleton**：先端到端最小可運行版本，新能力疊在已可運作的產品上；不為未完成的複雜度犧牲可運作狀態。
- **Structure Follows Need**：結構隨實際需求生長。無空目錄、無單路徑巢狀、無預建技術分層。模組邊界依「會一起改變的理由」切，不依技術類型切。
- **One Obvious Way**：每種操作單一公開入口，並依「執行面」規範的入口交付。
- **Single Source of Truth**：依賴、設定、schema、文件各有唯一來源，其餘以連結引用。
- **Borrow Before Building**：先研究成熟產品與既有依賴的既定解法，不從零發明。沿用順序：既有依賴 → 標準庫 → 成熟函式庫 → 自寫；判準是整體複雜度，非依賴數量。斷言函式庫做不到之前，先查文件與型別。
- **Delete, Don't Deprecate**：過時路徑直接移除，不加相容層、fallback、遷移邏輯。移除對外契約屬難逆決定，依優先序另判。
- **Small Reversible Changes**：一次一事。重構、依賴升級各自獨立成一次變更；變更含清理，殘留即未完成。
- **Explicit Over Implicit**：無隱藏依賴、臨時路徑、未述副作用。
- **Measure Before Optimizing**。

## 決策與衝突

優先序：安全與可逆性 > 契約穩定 > SSoT > YAGNI。

- 可逆決定走 YAGNI，取當下最簡。
- 難逆決定（對外契約、資料 schema、持久化格式、儲存選型）依長期考量，不接受「先這樣之後再換」。
- 分不清 → 當難逆處理。

偏離規則不禁止，但須在對應位置留下一行；靜默偏離視為違規。盤點：`rg -n 'EXCEPTION:' --hidden --glob '!.git'`

```
EXCEPTION: <偏離哪條規則 + 理由> | 回收條件: <何時該移除>
```

## 專案結構與依賴

- 專案啟動第一件事是 `git init`，不必詢問。commit 與 push 仍需明確指示。
- 每個 Python 專案獨立 `.venv`，禁全域依賴。
- 遵循 Python 3.12+ 最新 PEP。嚴格禁止（不可 EXCEPTION 豁免）：舊版專案配置、已廢棄型態寫法、SQL/Shell 的 f-string 拼接、過時併發模式。
- 版本釘選並提交鎖檔，禁以 latest 作為穩定策略。新增依賴須在 commit 訊息寫理由。

## 執行面

約束交付方式，非僅程式碼結構。規範入口恰有兩個：

- 營運／管線：`python -m <pkg> <subcommand>`，子命令集中註冊於一處，`--help` 即完整清單，README 只連到此。
- 測試：`pytest <node-id>`，不自建測試包裝。

**可具名重現**：值得跑第二次的操作都要有名字；名字之外不承載狀態。終端是傳輸層，不是儲存層。

- 尚無名字的操作先加子命令再給指令。「先跑一次看看」不構成例外，診斷同規。不另開腳本檔包裝既有命令。
- 交付格式：每個操作恰好一行可複製指令 + 一句說明。
- 豁免：純環境探查且不重複執行（`python -V`）。跑第二次即須落成子命令。

驗收：丟掉 scrollback、換一台機器、clean checkout，能否原樣再做一次？不能 → 缺名字或有環境依賴。

```
✗ python -c "from proj.pipeline import run; run('ingest')"
✗ $env:MODE='dev'; python scripts/a.py
✗ cat > proj/task.py << 'EOF' ...
✓ python -m proj pipeline run --stage ingest
✓ pytest tests/test_ingest.py::test_schema
```

## 輸出

**語言**：對使用者的一切輸出使用中文——回覆、`docs/`、README、commit、issue、本包自有技能檔。

- 有通行中文譯名就用中文；無譯名或翻譯妨礙查找則保留原文（frontmatter、OpenAPI、embedding）。
- 套件、指令、檔名、技術與模型名稱、程式碼識別符一律保留原文。
- vendored 檔案不翻譯。

**形狀**：每個 session 自動套用 `i-have-adhd`，無須 `/i-have-adhd`。該技能是唯一來源，改規則去改它，或說「stop adhd mode」停用。「無開場與收尾寒暄」不豁免 Glass Box。

## 職責邊界

各來源回答的問題不重疊，同一事實只有一個擁有者。

| 來源 | 回答什麼 |
|---|---|
| GitHub Issues | 要做什麼 |
| `docs/` | 系統現在是什麼、為什麼 |
| AGENTS.md | Agent 必須怎麼做 |
| Code / Tests | 系統實際做什麼 |
| memsearch memory | 過去發生過什麼 |

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

canonical source 為 `skills/<name>/`；`.claude/skills` 以 symlink 指向它；Codex 直接掃 `.agents/skills`。

## 語意索引

`docs/` 是唯一來源，語意索引只是可重建快取。任何寫入 `docs/` 或 `CONTEXT.md` 的工作流在主任務成功後刷新它，指令見 `project-docs` 技能。

- 未安裝或索引失敗不得使主任務失敗，只回報「語意索引未更新」。
- 本包不為索引加 hook 或 watch，也不自行改 chunking。語意工具自己的擷取機制是它自己的事。
- 跨 session 記憶用語意工具的原生流程，不自建結構化歷史層，不改寫或 vendor 它的官方擷取流程。
- 記憶分兩層：`.memsearch/memory/*.md` 是可攜的 SSoT，跟著 repo；CLI、模型與各 agent 的官方整合屬機器層外部依賴，`apply.sh` 不攜帶也不修改使用者層設定，只檢查並提示。索引與模型快取是衍生資料，不進版控。
- 記憶與 `docs/` 的資料量差距大時，多的一方會以純粹的量壓過另一方，使檢索結果倒轉權威順序——問「為什麼這樣決定」拿回討論而非決策紀錄。發生時分開索引集合。

## 契約驅動

HTTP API 以 `openapi.yaml` 為唯一來源，models 與契約測試由其生成，皆為產物、禁手改。做法見 `api-contract` 技能。

- 契約測試只驗證實作符合 spec；業務行為與 regression 由手寫測試負責。契約全綠不代表行為正確。
- CI 必須重跑生成並確認零差異。有差異就修 spec 或重新生成，不得改產物。
