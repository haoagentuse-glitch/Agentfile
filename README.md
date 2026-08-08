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

## Session 紀錄（agentkit）

安裝一次，所有專案共用：

```bash
uv tool install --editable ./agentkit
```

在專案裡：

```bash
agentkit init
```

之後每次 session 結束，`SessionEnd` hook 自動把逐字稿解析成結構化紀錄。

```bash
agentkit status
```

```bash
agentkit doctor
```

紀錄放在 `<git-common-dir>/agentkit/`——主 worktree 與 linked worktree 解析到同一處，所以 Claude 與 Codex 跨 worktree 共用同一份歷史。在 `.git/` 底下，不進版控。

agentkit 只管**結構化歷史**：哪個 agent、哪個 model、哪個分支、動了哪些檔案、當時的 commit。語意檢索是另一層，兩者不互相依賴——agentkit 的程式碼裡不會出現任何 semantic backend 的名字，換掉它不用動 agentkit 一行。

## 誰擁有什麼

同一件事只有一個擁有者。這是整包的核心約束。

| 來源 | 回答什麼 | 誰維護 |
|---|---|---|
| GitHub Issues | 要做什麼 | `to-spec` / `to-tickets` |
| `docs/PROJECT.md`、`docs/architecture.md` | 系統是什麼、怎麼組起來 | `project-docs` |
| `CONTEXT.md`、`docs/adr/` | 詞彙、為什麼這樣決定 | `domain-modeling` |
| `openapi.yaml` | API 契約 | `api-contract` |
| `AGENTS.md` | 做事必須遵守什麼 | 你 |
| Code / Tests | 系統實際做什麼 | `implement` / `tdd` |

`docs/PROJECT.md` 不是 feature spec，也不是 task list。Issue 裡的規格不抄進 `docs/`。

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

`apply.sh` 是整棵樹複製，加東西不用改它。既有專案要拿到更新，重跑 `apply.sh` 只補新檔；覆蓋舊檔請手動處理（腳本刻意不覆寫）。

## 規範

見 [AGENTS.md](AGENTS.md)。這包自己也遵守它。
