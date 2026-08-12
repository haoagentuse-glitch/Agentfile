# agentfile — 專案隨身包

一套可搬移的開發規範與工作流程。套進任何新專案，讓 Claude 與 Codex 遵循同一組規則、讀同一份 skill。

自包含：不需要安裝任何外掛。所有 skill 都是本包內的檔案，`apply.sh` 複製過去就能用。

## core + profile

規則與 skill 分兩層，只有 active profile 的內容會進到目標專案，不會的東西 agent 讀不到，也就不可能誤用：

```
core/                 永遠啟用的共通能力（不變量、通用 skill）
profiles/software/     一般軟體工程專案特化規則與 skill
profiles/experimental/ 實驗型專案（RAG、agent 架構、ML/DL、模擬、檢索與排序、
                        最佳化、演算法比較）特化規則與 skill
```

`core/AGENTS.md` + `profiles/<active>/AGENTS.md` 串接成目標專案唯一一份 `AGENTS.md`；`.claude/settings.json` 同樣是 core + profile 合併；`profiles/<active>/records/` 的 schema 投影成目標的 `records/`。機制見 [ADR 0005](docs/adr/0005-core-profile-isolation.md)；experimental profile 三個 skill（`evidence-review`／`experiment-design`／`experiment-lint`）的 upstream 取捨見 [ADR 0006](docs/adr/0006-experimental-profile-upstream-evaluation.md)。

## 套用

```bash
./apply.sh <目標資料夾> [--profile software|experimental]
```

不帶 `--profile` 預設 `software`。加 `--dry-run` 先看會做什麼。已存在的檔案一律跳過，可重複執行。

它做的事：`git init` → skills 投影（core + profile 聯集）→ `.claude/` 設定（core + profile 合併）→ `AGENTS.md`（core + profile 串接）/ `CLAUDE.md` → `docs/agents/` 議題追蹤設定 → `records/`（profile 擁有的 schema，沒有就跳過）→ `LICENSES/` → `.gitignore`（core + profile 串接）。

也可以用來把既有專案納入本規範。

完整啟動（含建立 GitHub repo 與 `ready-for-agent` 標籤）在目標專案裡跑：

```
/kickoff
```

## 每日流程

```
/grill-me     把需求問到收斂           不產生檔案
/to-spec      發成 GitHub Issue        spec 只存在 Issue
/to-tickets   拆成可獨立認領的 ticket   帶阻塞關係
/implement    實作，內部驅動 tdd        一次一張
/code-review  兩軸審查
/handoff      交接給下一個 session      寫在 OS 暫存目錄
```

`experimental` profile 的日常換成：`/evidence-review`（重大選型前先看證據）→ `/experiment-design`（凍結 Experiment Contract）→ `experiment-lint`（確定性檢查 Contract 可不可識別，通過才 lock）→ 跑 → 記錄進 `records/experiments/runs/` → `compare-runs`（確定性判定可比較性，再算指標差異，取捨依據見 [ADR 0007](docs/adr/0007-compare-runs-design.md)）→ `claim-audit`（機械核對數字跟引用，agent 判斷結論有沒有超出證據範圍，見 [ADR 0008](docs/adr/0008-claim-audit-design.md)）。要不要升到下一個 Compute Gate 等級（L0-L5）用 `compute-gate` 技能機械判定，規則怎麼翻成可比對的參數見 [ADR 0009](docs/adr/0009-compute-gate-design.md)。結果不好時先用 `diagnose-experiment`（探測 → 假設 → smoke → 控制變因 → 下結論，見 [ADR 0011](docs/adr/0011-diagnose-experiment-design.md)），不得直接調參。細節見 `profiles/experimental/AGENTS.md`。

系統長相改變時另外跑 `/project-docs`；詞彙或架構決策改變時跑 `/domain-modeling`；HTTP API 動到契約時跑 `/api-contract`。

要圖形化看 `records/experiments/` 裡的實驗、run、比較結果，用 `viewer/experiment-viewer/`（Tauri + Vue + TypeScript + ECharts，只讀不寫，不維護第二份權威副本）。設計與工具鏈取捨見該目錄 README 與 [ADR 0012](docs/adr/0012-experiment-viewer-toolchain.md)。

## 跨 session 記憶（memsearch）

跨 session 的對話記憶與檢索全部交給 memsearch 的原生流程，這包不自建。

```
對話 → 摘要 → memory Markdown → embedding / BM25 / RRF → recall → 逐字稿 fallback
```

不加 reranker、不接 GPU（不自行改 chunking 等既有規則見 [AGENTS.md「檢索」](AGENTS.md#檢索)）。

專案層（`.memsearch/memory/*.md`）與機器層（memsearch CLI、embedding 模型、各 agent 官方整合）分開，`apply.sh` 只檢查後者是否存在，不攜帶也不修改。`.memsearch/` **預設不進版控**，記憶留在本機；要跨機器帶著走，自行在 `.gitignore` 加回 `!.memsearch/memory/*.md`。決策理由見 [ADR 0001](docs/adr/0001-memsearch-two-layer-memory.md)、[ADR 0002](docs/adr/0002-memsearch-memory-not-tracked-by-default.md)；部件關係與已知限制見 [architecture.md](docs/architecture.md)。

### 機器層安裝

各機器裝一次，依執行環境而非帳號——同一個 WSL user 下切換帳號不必重裝。換 Desktop、OS 或 runtime 才需要各自再裝。

```bash
uv tool install "memsearch[onnx]"
```

Claude Code 的對話擷取整合（在 Claude Code 裡跑，沒有 CLI 方式）：

```
/plugin marketplace add zilliztech/memsearch-plugins
```

```
/plugin install memsearch
```

Codex 的整合（需 codex v0.116.0+）：

```bash
git clone https://github.com/zilliztech/memsearch.git && bash memsearch/plugins/codex/scripts/install.sh
```

`apply.sh` **不會**碰使用者層的外掛或 hook，只在最後列出缺哪些 runtime 與安裝方式。

memsearch **預設 embedding provider 是 OpenAI**，不設定會在第一次索引時因缺 `OPENAI_API_KEY` 直接失敗；切本機模型的下載大小與快取路徑見 [architecture.md](docs/architecture.md) 的「已知限制」節。要用本機模型，裝 `[onnx]` extra 並切換：

```bash
memsearch config set embedding.provider onnx
```

`apply.sh` **不會**觸發下載——套用這包不需要語意層，它是選用的。不想拉本機模型就跳過上面那步，改用 `openai`、`ollama`、`google`、`voyage`、`jina`、`mistral` 其中之一。

```bash
memsearch search "為什麼契約用 spec-first"
```

`docs/` 的索引**不需要手動維護**。寫 `docs/` 的工作流（`project-docs`、`domain-modeling`）在文件寫完後自己刷新；沒裝 memsearch 或索引失敗時的處理方式見 [AGENTS.md「檢索」](AGENTS.md#檢索)。

換成別的語意工具不用改這包任何東西——接軌只是「markdown 放在 `docs/`」這個慣例。已實測的成本與已知限制見 [architecture.md](docs/architecture.md)。

## 誰擁有什麼

同一件事只有一個擁有者，完整清單見 [AGENTS.md 職責邊界](AGENTS.md#職責邊界)。

## skill 放在哪

```
core/skills/<name>/              core skill canonical source
profiles/<name>/skills/<name>/   該 profile 特化 skill canonical source
.claude/skills                   → ../.agents/skills（symlink，聯集後的投影，這包自己也吃這套機制）
```

套用到目標專案後：

```
.agents/skills/       真實檔案（core + active profile 聯集），Codex 直接掃這裡
.claude/skills        → ../.agents/skills（symlink）
```

不做 `.codex/skills/` 投影——Codex 從 cwd 往上掃 `.agents/skills`，再投影一次就是第二條路徑。

symlink 在 Windows 原生環境不可靠；WSL、macOS、Linux 正常。

## vendored skills

以下取自 [mattpocock/skills](https://github.com/mattpocock/skills)（MIT，授權全文在 `LICENSES/`），逐字保留：

- **core**（`core/skills/`）：`grilling` `grill-me` `grill-with-docs` `writing-for-agents` `domain-modeling` `handoff`
- **software profile**（`profiles/software/skills/`）：`codebase-design` `to-spec` `to-tickets` `tdd` `implement` `code-review`

另取自 [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd)（MIT）：`i-have-adhd`（core）。它是輸出形狀的唯一來源，規則不複製到別的檔案。手動輸入 `/i-have-adhd` 啟用；要關掉就說「stop adhd mode」。

每份的 frontmatter `metadata` 記著來源 commit。改動只有兩處，都不碰 workflow：

- 注入 `metadata.source` / `metadata.license`
- 上游要求跑 `/setup-matt-pocock-skills` 的地方，改指向本包交付的 `docs/agents/issue-tracker.md`

本包自有：`asd-ste100` `project-docs` `rule-check` `zh-lint`（core）、`project-bootstrap` `api-contract`（software profile）

另從 [fcakyon/phd-skills](https://github.com/fcakyon/phd-skills)（MIT，授權全文在 `LICENSES/`）**裁切改編**（不是逐字保留）三個技能到 `profiles/experimental/skills/`：`experiment-design`（最小修改）、`evidence-review`（裁自上游 `literature-research`，砍掉找論文缺口的部分，換成本包的 Research Gate 輸出格式）、`diagnose-experiment`（裁自上游 `debug`，五步紀律整段保留，探測清單跟 smoke 對照表從 ML 訓練專屬泛化成 RAG／agent 架構／模擬／最佳化與演算法比較都適用的 failure taxonomy，見 [ADR 0011](docs/adr/0011-diagnose-experiment-design.md)）。取捨依據跟哪些段落改了什麼，記在 [ADR 0006](docs/adr/0006-experimental-profile-upstream-evaluation.md)，不在這裡重述。`experiment-lint`、`compare-runs`、`claim-audit`、`compute-gate` 是本包自寫的，不是 vendor 來的——`compare-runs` 只借了 phd-skills/compare 兩條規則的精神（見 [ADR 0007](docs/adr/0007-compare-runs-design.md)），`claim-audit` 只借了 ARA 論文的 claim→experiment→evidence 綁定概念（ARA 本身沒有可 vendor 的實作，見 [ADR 0008](docs/adr/0008-claim-audit-design.md)），`compute-gate` 只借了 Scholar Loop 的分級漏斗形狀（不碰它的自動決策機制，見 [ADR 0006](docs/adr/0006-experimental-profile-upstream-evaluation.md)、[ADR 0009](docs/adr/0009-compute-gate-design.md)）。判定邏輯與輸出格式都是自己設計。

### 更新 vendored skill

刻意行為，不自動同步。比對上游後決定是否採納：

```bash
diff <(curl -sS https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md) profiles/software/skills/tdd/SKILL.md
```

採納後記得更新 `metadata.source` 的 commit。

## 怎麼擴充

- **加規則** → 跨所有 profile 都成立就改 `core/AGENTS.md`；只有某個 profile 需要就改 `profiles/<name>/AGENTS.md`。不要複製到別的檔案。
- **加能力** → 通用就在 `core/skills/<name>/SKILL.md` 新增，某個 profile 特有就放 `profiles/<name>/skills/<name>/SKILL.md`。先確認沒有既有 skill 已經涵蓋——同一能力不得存在兩份，也不得同一份重複出現在 core 跟某個 profile 裡。
- **從別處借 skill** → vendor 進對應層的 `skills/`，出處寫進 `metadata`，授權放 `LICENSES/`。
- **加文件骨架** → 通用放 `core/.claude/templates/`，profile 特化放 `profiles/<name>/.claude/templates/`。
- **這台機器/這個人專屬的規範覆寫** → 專案根目錄 `CLAUDE.local.md`，Claude Code 原生機制，已在 `.gitignore` 排除。Codex 目前沒有對應機制。

`apply.sh` 對 `core/skills/`、`profiles/<active>/skills/`、`.claude/` 都是整棵樹複製，不 symlink 指回這包本身——理由見 [ADR 0003](docs/adr/0003-apply-copies-not-symlinks-to-dotfiles.md)。加 skill、加文件骨架不用改 `apply.sh`；新增一個 profile（目前只有 `software`／`experimental` 兩個）才要改腳本裡的合法值檢查。既有專案要拿到更新，重跑 `apply.sh` 只補新檔；覆蓋舊檔請手動處理（腳本刻意不覆寫）。

## 規範

見 [AGENTS.md](AGENTS.md)。這包自己也遵守它。
