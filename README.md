# agentfile — 專案隨身包

一套可搬移的開發規範與工作流程。套進任何專案，讓 Claude 與 Codex 遵循同一組規則、讀同一份 skill。

不需要安裝外掛。所有 skill 都是本包內的檔案，複製過去就能用。

## 套用

```bash
./apply.sh <目標資料夾> [--profile software|experimental] [--dry-run]
```

不帶 `--profile` 預設 `software`。可重複執行，也可以拿來把既有專案納入本規範。

之後在目標專案裡跑 `/kickoff` 完成 GitHub repo 與標籤設定。

要更新既有專案，直接重跑同一行。沒被你改過的投影檔會換成新版，你改過的不動並列在摘要裡等你處理；`AGENTS.md` 與 `.gitignore` 末尾的專案特化段一律保留。機制見 [ADR 0014](docs/adr/0014-apply-manifest-based-update.md)。

## 兩種模式

只有 active profile 的規則與 skill 會進到目標專案。沒進去的東西 agent 讀不到，也就不可能誤用。

| profile | 用在 | 核心約束 |
|---|---|---|
| `software` | 一般軟體工程 | spec → ticket → TDD → review，契約與文件有單一擁有者 |
| `experimental` | RAG、agent 架構、ML/DL、模擬、檢索排序、最佳化、演算法比較 | 結論必須能追到證據；混雜的比較不得下因果結論 |

`core/AGENTS.md` + `profiles/<active>/AGENTS.md` 串成目標專案唯一一份 `AGENTS.md`。機制見 [ADR 0005](docs/adr/0005-core-profile-isolation.md)。

## 每日指令：software

| 指令 | 做什麼 |
|---|---|
| `/grill-me` | 把需求問到收斂，不產生檔案 |
| `/to-spec` | 發成 GitHub Issue，spec 只存在 Issue |
| `/to-tickets` | 拆成可獨立認領的 ticket，帶阻塞關係 |
| `/implement` | 實作，內部驅動 TDD，一次一張 |
| `/code-review` | 標準與規格兩軸審查 |
| `/handoff` | 交接給下一個 session |

系統長相改變時跑 `/project-docs`；詞彙或架構決策改變跑 `/domain-modeling`；HTTP API 動到契約跑 `/api-contract`。

## 每日指令：experimental

| 順序 | 指令 | 做什麼 |
|---|---|---|
| 1 | `/evidence-review` | 重大選型前先看證據 |
| 2 | `/experiment-design` | 凍結 Contract，含研究問題憑證與算力階梯 |
| 3 | `experiment-lint` | 機械驗證，通過才 lock |
| 4 | — | 跑，紀錄進 `records/experiments/runs/` |
| 5 | `compute-gate` | 能不能升到下一級，由 Contract 凍結的門檻判定 |
| 6 | `compare-runs` | 先判可比較性，才算指標差異 |
| 7 | `claim-audit` | 核對數字與引用，再判結論有沒有超出證據範圍 |
| 8 | `diagnose-experiment` | 結果不好時先診斷，不得直接調參 |

三條不能繞過的規則：

- **跑失敗是正式結果。** 標 `invalid` 並填 `failure`，不刪除。診斷寫進 `records/experiments/diagnoses/`。
- **語意稽核要獨立。** 用 `experiment_records review-package` 組出審核包，換一個 context 或換一個人看。包裡沒有產出者資訊。
- **門檻與審核政策跟 Contract 一起凍結。** 看到結果之後才放寬標準，等於沒有標準。

完整走過一遍的樣子在 `profiles/experimental/fixtures/rag-walkthrough/`。細節見 `profiles/experimental/AGENTS.md`，設計理由見 [ADR 0013](docs/adr/0013-frontier-research-agent-methodology-evaluation.md)。

圖形化瀏覽實驗紀錄用 [`viewer/experiment-viewer/`](viewer/experiment-viewer/README.md)。

## 跨 session 記憶

交給 memsearch 的原生流程，這包不自建、不加 reranker、不改 chunking。

各機器裝一次（依執行環境而非帳號）：

```bash
uv tool install "memsearch[onnx]"
memsearch config set embedding.provider onnx
```

第二行必跑。memsearch 預設 embedding provider 是 OpenAI，不切成本機模型的話，第一次索引會因為缺 `OPENAI_API_KEY` 直接失敗。本機模型首次索引要下載約 558 MB，之後快取在 `~/.cache/huggingface/`。

查詢：

```bash
memsearch search "為什麼契約用 spec-first"
```

Claude Code 的對話擷取整合（只能在 Claude Code 裡跑）：

```
/plugin marketplace add zilliztech/memsearch-plugins
/plugin install memsearch
```

Codex 整合（需 codex v0.116.0+）：

```bash
git clone https://github.com/zilliztech/memsearch.git && bash memsearch/plugins/codex/scripts/install.sh
```

`apply.sh` 不碰使用者層外掛、不觸發模型下載，只在最後列出缺哪些 runtime。`.memsearch/` 預設不進版控；要跨機器帶著走，自行在 `.gitignore` 加回 `!.memsearch/memory/*.md`。`docs/` 的索引不用手動維護，寫 `docs/` 的工作流會自己刷新。

## 檔案放哪

`<active>` 是 `--profile` 選中的那個。未啟用的 profile 完全不會出現在套用後的專案裡。

| 本包內 | 怎麼過去 | 套用後 |
|---|---|---|
| `core/AGENTS.md` + `profiles/<active>/AGENTS.md` | 串接，profile 在後 | `AGENTS.md` |
| `CLAUDE.md` | 複製 | `CLAUDE.md` |
| `core/skills/` + `profiles/<active>/skills/` | 聯集複製，同名先到者贏 | `.agents/skills/` |
| `profiles/<active>/tools/` | 複製 | `.agents/tools/` |
| `profiles/<active>/records/` | 複製，只有 schema 與 prompt | `records/` |
| `core/.claude/` + `profiles/<active>/.claude/` | 聯集複製 | `.claude/` |
| 兩層的 `settings.json` | `jq` 合併允許與拒絕清單 | `.claude/settings.json` |
| 兩層的 `gitignore.base` | 串接 | `.gitignore` |
| `core/.claude/templates/agents/` | 複製 | `docs/agents/` |
| `docs/THIRD_PARTY_LICENSES.md` | 複製 | 同路徑 |
| —— | `apply.sh` 產生 | `.agentfile/` 來源 revision 與投影紀錄 |

只有一條不是複製而是指標：`.claude/skills → ../.agents/skills`（symlink）。Claude 讀 `.claude/skills`、Codex 從 cwd 往上掃 `.agents/skills`，兩邊指向同一份檔案，改 skill 只改一處。不另做 `.codex/skills/` 投影。symlink 在 Windows 原生環境不可靠，WSL、macOS、Linux 正常。

要加東西：

| 要加什麼 | 放哪 |
|---|---|
| 跨 profile 都成立的規則 | `core/AGENTS.md` |
| 只有某個 profile 的規則 | `profiles/<name>/AGENTS.md` |
| 通用能力 | `core/skills/<name>/SKILL.md` |
| profile 特有能力 | `profiles/<name>/skills/<name>/SKILL.md` |
| 文件骨架 | `<層>/.claude/templates/` |
| 這台機器專屬的覆寫 | 專案根目錄 `CLAUDE.local.md`（已在 `.gitignore`） |

同一能力不得存在兩份，也不得同時出現在 core 與某個 profile。加 skill 不用改 `apply.sh`；新增 profile 才要改腳本裡的合法值檢查。

改完 `apply.sh` 要跑：

```bash
uv run pytest tests/test_apply.py
```

那支測試逐格驗證更新判定表。完整驗收不只這一套：

| 指令 | 驗收範圍 |
|---|---|
| `uv run --frozen ruff check tests profiles/experimental/tools/experiment-records/src profiles/experimental/tools/experiment-records/tests` | Python 語法、import 與未使用名稱 |
| `uv run --frozen pytest` | `apply.sh` 投影、更新與下游 CLI |
| `uv run --project profiles/experimental/tools/experiment-records --frozen pytest profiles/experimental/tools/experiment-records/tests` | experimental schema、生命週期與確定性工具 |
| `npm --prefix viewer/experiment-viewer ci` | 安裝 Viewer 鎖定依賴 |
| `npm --prefix viewer/experiment-viewer audit --audit-level=high` | 阻擋 Viewer high／critical 已知弱點 |
| `npm --prefix viewer/experiment-viewer test` | Viewer 資料層與 Vue 元件 |
| `npm --prefix viewer/experiment-viewer run build` | TypeScript 與 production build |
| `npm --prefix viewer/experiment-viewer run release:windows` | Windows Rust tests、portable PE 與 NSIS installer；只能在 NTFS checkout 執行 |

`.github/workflows/ci.yml` 在 push 與 pull request 重跑同一組 gate。

## 規範

見 [AGENTS.md](AGENTS.md)。這包自己也遵守它。

套用這包的專案在使用中發現規範本身有缺口，用 `upstream-feedback` 技能回報到本 repo 的 Issue（label `agentfile-feedback`），不在下游改寫上游條文。判準與處理流程見該技能，決策理由見 [ADR 0015](docs/adr/0015-upstream-feedback-via-issues.md)。

## 第三方

vendored skill 改寫成中文，規則不增不減；每份的 frontmatter 記著來源 commit 與改寫狀態。不自動同步，更新時比對上游自己的兩個 commit——`metadata.source` 記的那個與現在的上游——看那段期間改了什麼再決定採不採納：

```bash
diff <(curl -sS https://raw.githubusercontent.com/mattpocock/skills/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/tdd/SKILL.md) <(curl -sS https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md)
```

- [mattpocock/skills](https://github.com/mattpocock/skills)（MIT）— 改寫成中文，理由見 [ADR 0020](docs/adr/0020-vendored-skills-in-chinese.md)
- [fcakyon/phd-skills](https://github.com/fcakyon/phd-skills)（MIT）— 裁切改編後改寫成中文，改了哪些段落見 [ADR 0006](docs/adr/0006-experimental-profile-upstream-evaluation.md)

其餘 skill 為本包自寫。授權全文見 [docs/THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md)。
