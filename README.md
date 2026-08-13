# agentfile — 專案隨身包

一套可搬移的開發規範與工作流程。套進任何專案，讓 Claude 與 Codex 遵循同一組規則、讀同一份 skill。

不需要安裝外掛。所有 skill 都是本包內的檔案，複製過去就能用。

## 套用

```bash
./apply.sh <目標資料夾> [--profile software|experimental] [--dry-run]
```

不帶 `--profile` 預設 `software`。已存在的檔案一律跳過，可重複執行，也可以拿來把既有專案納入本規範。

之後在目標專案裡跑 `/kickoff` 完成 GitHub repo 與標籤設定。

要更新既有專案，重跑 `apply.sh` 只補新檔；覆蓋舊檔請手動處理（腳本刻意不覆寫）。

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
memsearch config set embedding.provider onnx    # 不設定的話預設 OpenAI，缺金鑰會在第一次索引失敗
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

```
本包內                              套用後
core/skills/<name>/            ┐
profiles/<name>/skills/<name>/ ┴──→  .agents/skills/   Codex 直接掃這裡
profiles/<name>/tools/<name>/  ───→  .agents/tools/
profiles/<name>/records/       ───→  records/
                                     .claude/skills → ../.agents/skills（symlink）
```

不做 `.codex/skills/` 投影——Codex 會從 cwd 往上掃 `.agents/skills`。symlink 在 Windows 原生環境不可靠，WSL、macOS、Linux 正常。

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

## 規範

見 [AGENTS.md](AGENTS.md)。這包自己也遵守它。

## 第三方

vendored skill 逐字保留上游內文，只注入來源 metadata；每份的 frontmatter 記著來源 commit。不自動同步，更新時手動比對上游後再決定是否採納：

```bash
diff <(curl -sS https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md) profiles/software/skills/tdd/SKILL.md
```

- [mattpocock/skills](https://github.com/mattpocock/skills)（MIT）— 逐字保留
- [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd)（MIT）— 逐字保留，手動輸入 `/i-have-adhd` 啟用
- [fcakyon/phd-skills](https://github.com/fcakyon/phd-skills)（MIT）— 裁切改編，改了哪些段落見 [ADR 0006](docs/adr/0006-experimental-profile-upstream-evaluation.md)

其餘 skill 為本包自寫。授權全文見 [docs/THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md)。
