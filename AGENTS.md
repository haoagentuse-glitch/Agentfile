# AGENTS.md

唯一規範來源。CLAUDE.md 僅以一行引用本檔。專案特化章節只追加於末尾，不改寫上游條文。

## 核心原則

- **KISS / YAGNI**：只做當下所需，選能完全滿足現況的最簡實作。禁推測性抽象、設定與過度間接轉介。
- **Optimize for Comprehension**：降低理解成本優先於降低操作成本。抽象須提升可理解性，不得只縮短指令或隱藏細節。
  - 順向（Discoverability / Shallow Abstraction）：公開入口到實際邏輯 ≤ 2 跳，不需追 registry／factory／dispatcher 才找得到。僅轉呼叫另一入口的層直接折疊，禁 wrapper chain。限自有程式碼路徑，第三方庫不計跳數。
  - 逆向（Traceability / Glass Box）：任何結果可回溯至命令、設定、輸入與 commit。入口預設輸出這四項摘要，不得只回 `Done.`；禁未述副作用。
- **Walking Skeleton**：先端到端最小可運行版本，新能力疊在已可運作的產品上；不為未完成的複雜度犧牲可運作狀態。
- **Structure Follows Need**：結構隨實際需求生長。無空目錄、無單路徑巢狀、無預建技術分層。模組邊界依「會一起改變的理由」切，不依技術類型切；功能聚合優先，關注點分離。
- **One Obvious Way**：每種操作單一公開入口，並依「執行面」規範的入口交付執行。
- **Single Source of Truth**：依賴、設定、schema、文件各有唯一來源，其餘以連結引用。
- **Borrow Before Building**：先研究成熟產品與既有依賴的既定解法，採用已驗證模式，不從零發明。沿用順序：既有依賴 → 標準庫 → 成熟函式庫 → 自寫；判準是整體複雜度，非依賴數量。斷言函式庫做不到之前，先查文件與型別。
- **Delete, Don't Deprecate**：過時路徑直接移除，不加相容層、fallback、遷移邏輯，不保留向下相容。移除對外契約屬難逆決定，依優先序另判。
- **Small Reversible Changes**：一次一事。重構、依賴升級各自獨立成一次變更；變更含清理，殘留即未完成。
- **Explicit Over Implicit**：無隱藏依賴、臨時路徑、未述副作用。
- **Measure Before Optimizing**。

## 決策與衝突

優先序：安全與可逆性 > 契約穩定 > SSoT > YAGNI。

- 可逆決定：走 YAGNI，取當下最簡。
- 難逆決定（對外契約、資料 schema、持久化格式、儲存選型）：依長期考量，不接受「先這樣之後再換」的權宜之計。
- 分不清 → 當難逆處理。

## 例外機制

偏離規則不禁止，但須在對應位置留下一行；靜默偏離視為違規。

```
EXCEPTION: <偏離哪條規則 + 理由> | 回收條件: <何時該移除>
```

盤點：`rg -n 'EXCEPTION:' --hidden --glob '!.git'`

## 專案結構與依賴

- 專案啟動第一件事是 `git init`，屬起手動作，不必詢問。commit 與 push 仍需明確指示。
- 環境隔離：每個 Python 專案獨立 `.venv`，禁全域依賴。
- 遵循 Python 3.12+ 最新 PEP。嚴格禁止（不可用 EXCEPTION 豁免）：舊版專案配置、已廢棄型態寫法、SQL/Shell 的 f-string 拼接、過時併發模式。
- 依賴鎖定：版本釘選並提交鎖檔，禁以 latest 作為穩定策略。
- 單一入口：對外操作唯一入口，位置見 README。
- 腳本邊界：不另開腳本檔包裝既有命令；固定多步驟流程落成單一公開入口（CLI 為預設實作），入口須滿足 Optimize for Comprehension。
- 新增依賴須在 commit 訊息寫理由。

## 執行面

約束交付方式，非僅程式碼結構。規範入口恰有兩個：

- 營運／管線：專案宣告的單一入口（預設 `python -m <pkg> <subcommand> [args]`），子命令集中註冊於一處，`--help` 即完整清單（README 只連到此，不複述）
- 測試：`pytest <node-id>`，不自建測試包裝

**可具名重現（Named & Hermetic）**：值得跑第二次的操作都要有名字；名字之外不承載狀態。終端是傳輸層，不是儲存層。

- 尚無名字的操作：先加子命令再給指令。「先跑一次看看」不構成例外；診斷同規。
- 新增子命令屬單一入口的擴充；另開腳本檔才算第二入口。
- 交付格式：每個操作恰好一行可複製指令 + 一句說明。
- Glass Box 的預設輸出為摘要而非全量 log；管線串接場景提供 `--quiet`／機器可讀輸出。
- 豁免：純環境探查且不重複執行（`python -V`）。跑第二次即須落成子命令。

驗收：丟掉 scrollback、換一台機器、clean checkout，這件事能否原樣再做一次？不能 → 缺名字或有環境依賴。記不住的呼叫同樣是缺名字，落成 profile 或子命令。

```
✗ python -c "from proj.pipeline import run; run('ingest')"
✗ $env:MODE='dev'; python scripts/a.py
✗ cat > proj/task.py << 'EOF' ...
✓ python -m proj pipeline run --stage ingest
✓ pytest tests/test_ingest.py::test_schema
```

## 技能 vendoring

- 每個能力只有一份實作。來源不限，同一能力不得存在兩份。
- 外部技能 vendor 成本包自有檔案，不以外掛安裝。外掛裝在使用者層級，clean checkout 換機就散，違反「執行面」的驗收。
- vendored 檔案逐字保留，只允許：注入出處 metadata、把上游的 per-repo 設定引用改指向本包交付的設定檔。不改 workflow 內文。
- 出處記於 frontmatter 的 `metadata`，含來源 repo、commit、授權。授權全文放 `LICENSES/`。
- 更新是刻意行為：手動 diff 上游後決定是否採納，不自動同步。

canonical source 是 `skills/<name>/`。`.claude/skills` 是指向它的 symlink；Codex 直接掃 `.agents/skills`，不另做投影。

## 權威順序

**只適用於判斷「專案現況與歷史事實」，不適用於決定該怎麼做事。**

```
Code / Tests → Current Docs / ADR → AGENTS.md → Handoff → Conversation Memory → Raw Transcript
```

- 工程行為一律遵守 AGENTS.md。現況違反規範時那是待修的偏離，不是可援引的先例——舊專案留著 `requirements.txt` 不會讓 `pyproject.toml + uv` 這條失效。
- Memory 只解釋歷史，不覆蓋現行 code/docs。
- Handoff 是 session 間的暫存交接文件，寫在 OS 暫存目錄，不進版控。

各來源回答的問題不重疊：

| 來源 | 回答什麼 |
|---|---|
| GitHub Issues | 要做什麼 |
| `docs/` | 系統現在是什麼、為什麼這樣 |
| AGENTS.md | Agent 做事必須遵守什麼 |
| Code / Tests | 系統實際做什麼 |
| agentkit | 過去發生過什麼 |

`docs/PROJECT.md` 是目的、範圍、系統概觀與穩定背景，不是 feature spec，不是 task list。不得把 issue 裡的 spec 抄一份進 `docs/`。

## 契約驅動

HTTP API 以 `openapi.yaml` 為唯一來源，models 與契約測試由它生成，兩者皆為產物，禁手改。

測試分工：

- 契約測試（schemathesis）只驗實作是否遵守 spec：回應符合 schema、無未宣告的 500、宣告的限制確實拒絕。
- 業務行為與 regression 由手寫測試負責，走 TDD 的 red-green-refactor。契約全綠不代表行為正確。
- 不禁止手寫測試案例。契約測試縮小了手寫測試要涵蓋的面，不取代它。

產物仍會漂移，CI 必須驗證：重跑生成後 `git diff --exit-code`，非空即紅。修 spec 或重新生成，不得改產物解決。
移除或破壞已發布的對外契約屬難逆決定，先記 ADR 再改 spec。
