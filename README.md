# agentfile — 專案隨身包

一套可搬移的開發規範與工作流程。套進任何新專案，讓 Claude 與 Codex 遵循同一組規則、讀同一份 skill。

自包含：不需要安裝任何外掛。所有 skill 都是本包內的檔案，`apply.sh` 複製過去就能用。

## 套用

```bash
./apply.sh <目標資料夾>
```

加 `--dry-run` 先看會做什麼。已存在的檔案一律跳過，可重複執行。

它做的事：`git init` → skills 投影 → `.claude/` 設定 → `AGENTS.md` / `CLAUDE.md` → `docs/agents/` tracker 設定 → `LICENSES/` → `.gitignore`。

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

系統長相改變時另外跑 `/project-docs`；詞彙或架構決策改變時跑 `/domain-modeling`；HTTP API 動到契約時跑 `/api-contract`。

## 跨 session 記憶（memsearch）

跨 session 的對話記憶與檢索全部交給 memsearch 的原生流程，這包不自建。

```
對話 → 摘要 → memory Markdown → embedding / BM25 / RRF → recall → 逐字稿 fallback
```

不自行改 chunking、不加 reranker、不接 GPU。

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

memsearch 的**預設 embedding provider 是 OpenAI**，不設定的話第一次索引會因為缺 `OPENAI_API_KEY` 直接失敗。要用本機模型得裝 `[onnx]` extra 並切換：

```bash
memsearch config set embedding.provider onnx
```

> **切換後首次 `memsearch index` 會從 HuggingFace 下載約 558 MB 的 bge-m3 int8 模型**，之後快取在家目錄。本機 CPU 執行，不需 API key。安裝本身不下載，只有第一次索引才會。
>
> 模型快取在 `~/.cache/huggingface/`（實測 560 M），索引在 `~/.memsearch/milvus.db`。兩者都在家目錄，不在 repo 內，也不進版控。`apply.sh` **不會**觸發下載——套用這包不需要語意層，它是選用的。
>
> 不想拉本機模型就跳過上面那步，改用 `openai`、`ollama`、`google`、`voyage`、`jina`、`mistral` 其中之一。

```bash
memsearch search "為什麼契約用 spec-first"
```

`docs/` 的索引**不需要手動維護**。寫 `docs/` 的工作流（`project-docs`、`domain-modeling`）在文件寫完後自己刷新。沒裝 memsearch 或索引失敗都不會讓文件任務失敗，只會在回報末尾說一句索引未更新。

換成別的語意工具不用改這包任何東西——接軌只是「markdown 放在 `docs/`」這個慣例。已實測的成本與已知限制見 [architecture.md](docs/architecture.md)。

## 誰擁有什麼

同一件事只有一個擁有者，完整清單見 [AGENTS.md 職責邊界](AGENTS.md#職責邊界)。

## skill 放在哪

```
skills/<name>/        canonical source（本包唯一真本）
.claude/skills        → ../skills（symlink）
```

套用到目標專案後：

```
.agents/skills/       真實檔案，Codex 直接掃這裡
.claude/skills        → ../.agents/skills（symlink）
```

不做 `.codex/skills/` 投影——Codex 從 cwd 往上掃 `.agents/skills`，再投影一次就是第二條路徑。

symlink 在 Windows 原生環境不可靠；WSL、macOS、Linux 正常。

## vendored skills

以下取自 [mattpocock/skills](https://github.com/mattpocock/skills)（MIT，授權全文在 `LICENSES/`），逐字保留：

`grilling` `grill-me` `grill-with-docs` `writing-for-agents` `domain-modeling` `codebase-design` `to-spec` `to-tickets` `tdd` `implement` `code-review` `handoff`

另取自 [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd)（MIT）：`i-have-adhd`。它是輸出形狀的唯一來源，規則不複製到別的檔案。手動輸入 `/i-have-adhd` 啟用；要關掉就說「stop adhd mode」。

每份的 frontmatter `metadata` 記著來源 commit。改動只有兩處，都不碰 workflow：

- 注入 `metadata.source` / `metadata.license`
- 上游要求跑 `/setup-matt-pocock-skills` 的地方，改指向本包交付的 `docs/agents/issue-tracker.md`

本包自有：`project-bootstrap` `rule-check` `project-docs` `api-contract`

### 更新 vendored skill

刻意行為，不自動同步。比對上游後決定是否採納：

```bash
diff <(curl -sS https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md) skills/tdd/SKILL.md
```

採納後記得更新 `metadata.source` 的 commit。

## 怎麼擴充

- **加規則** → 改 `AGENTS.md`。不要複製到別的檔案。
- **加能力** → 在 `skills/<name>/SKILL.md` 新增。先確認沒有既有 skill 已經涵蓋——同一能力不得存在兩份。
- **從別處借 skill** → vendor 進 `skills/`，出處寫進 `metadata`，授權放 `LICENSES/`。
- **加文件骨架** → 放 `.claude/templates/`。
- **這台機器/這個人專屬的規範覆寫** → 專案根目錄 `CLAUDE.local.md`，Claude Code 原生機制，已在 `.gitignore` 排除。Codex 目前沒有對應機制。

`apply.sh` 是整棵樹複製，不 symlink 指回這包本身——理由見 [ADR 0003](docs/adr/0003-apply-copies-not-symlinks-to-dotfiles.md)。加東西不用改它。既有專案要拿到更新，重跑 `apply.sh` 只補新檔；覆蓋舊檔請手動處理（腳本刻意不覆寫）。

## 規範

見 [AGENTS.md](AGENTS.md)。這包自己也遵守它。
