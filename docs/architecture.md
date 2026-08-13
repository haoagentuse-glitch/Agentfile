# agentfile — 架構

## 部件

| 部件 | 做什麼 | 誰讀它 |
|---|---|---|
| `core/AGENTS.md` | 跨 profile 都成立的不變量，唯一規範來源的 upstream 部分 | `apply.sh` 串接進目標專案的 `AGENTS.md` |
| `profiles/<name>/AGENTS.md` | active profile 特化規則，追加於 core 之後 | 同上，只有 active profile 那份會被串接 |
| `core/skills/<name>/`、`profiles/<name>/skills/<name>/` | 技能 canonical source，依 core／profile 分層 | `apply.sh` 聯集複製進目標的 `.agents/skills/` |
| `core/.claude/`、`profiles/<name>/.claude/` | Claude Code 設定與 command 的 core／profile 來源 | `apply.sh` 合併（`settings.json` 用 `jq`，其餘用檔案聯集）|
| `profiles/<name>/records/` | 該 profile 擁有的權威 schema（例如 experimental 的實驗、run、指標三份 schema） | `apply.sh` 複製進目標的 `records/`；`definitions/`／`runs/` 這類使用者產生的內容不預建，用到才生 |
| `profiles/<name>/tools/` | active profile 的確定性工具 canonical source | `apply.sh` 複製進目標的 `.agents/tools/`；不混入 prompt skill |
| `apply.sh` | 依 `--profile` 投射規則、skills、tools、records 與第三方授權文件；重跑時依投影雜湊決定更新或保留 | 人工執行，可重跑 |
| 目標專案的 `.agentfile/` | `source.json` 記來源 revision 與 profile；`manifest.tsv` 記每個投影檔的雜湊、受管長度與模式 | `source.json` 給 agent 讀，`manifest.tsv` 只給 `apply.sh` 讀 |
| `.memsearch/memory/*.md` | 跨 session 記憶 SSoT，預設本機、不進版控 | memsearch CLI（機器層依賴，見下） |

agentfile 自己的根目錄 `AGENTS.md`／`.gitignore`／`.claude/settings.json`／`.claude/skills` 是手動組裝出跟 `apply.sh --profile software` 相同邏輯的結果——`apply.sh` 拒絕以自己為目標（見 [ADR 0003](adr/0003-apply-copies-not-symlinks-to-dotfiles.md)），所以這四個產物不會自動同步，改了 `core/` 或 `profiles/software/` 底下的來源要記得手動重跑組裝。

## 邊界

- `apply.sh` 只複製檔案與建 symlink，不安裝、不修改使用者層外掛設定——理由見 [ADR 0001](adr/0001-memsearch-two-layer-memory.md)。
- 跨 session 記憶預設不進版控，需要攜帶時使用者手動選擇追蹤——理由見 [ADR 0002](adr/0002-memsearch-memory-not-tracked-by-default.md)。
- `apply.sh` 複製整棵樹進目標專案，不 symlink 指回這包所在的家目錄——理由見 [ADR 0003](adr/0003-apply-copies-not-symlinks-to-dotfiles.md)。改成全域 symlink 是常見的「優化」，但會破壞規範與記憶只隨專案走的前提，改動前先讀這條 ADR。
- 重跑 `apply.sh` 會覆寫「與投影當下逐位元相同」的檔，只有這種檔。下游改過的一律不動並列進摘要，`AGENTS.md` 與 `.gitignore` 末尾的專案特化段在更新時保留——判定表與兩種 mode 見 [ADR 0014](adr/0014-apply-manifest-based-update.md)。行為由 `tests/test_apply.py` 逐格驗證，改 `apply.sh` 前先跑 `pytest tests/test_apply.py`。
- `.claude/skills` 與（投影後的）`.agents/skills` 都是 symlink 指回 core／profile 的 `skills/`，不是第二份拷貝；改 skill 只改一處。
- 記憶與文件都要主動策展，不是無限堆積——context 越大越雜，agent 表現越差。`docs/` 只在系統長相改變時才寫（不是每張票都跑），語意索引只收 `docs/`，不收整個對話逐字稿，都是把這個邊界落實成具體規則，而非一次性宣告。
- Graphify 是列為 optional 的未來結構檢索層，v1 未安裝——見 [ADR 0004](adr/0004-graphify-optional-structural-layer.md)。啟用門檻與範圍限制都在那裡，不要因為看到別人在用就直接開。
- 只有 active profile 的規則、skill、設定會出現在目標專案裡；未啟用 profile 的東西實體上不存在，不是靠文件告誡 agent 不要用——理由見 [ADR 0005](adr/0005-core-profile-isolation.md)。
- `experiment-lint` 只負責觸發 `.agents/tools/experiment-records` 的 canonical validator。Schema、project-ref、Contract config diff 與 lifecycle event 都由同一個 CLI 驗證。`compare-runs` 仍由 `compare_runs.py` 負責 run 可比較性。`claim-audit` 維持機械檢查與 agent 語意判斷分工。

## Experimental profile

七個 skill：`evidence-review`、`experiment-design`、`experiment-lint`、`compare-runs`、`claim-audit`、`compute-gate`、`diagnose-experiment`。取捨依據分別見 [ADR 0006](adr/0006-experimental-profile-upstream-evaluation.md)、[0007](adr/0007-compare-runs-design.md)、[0008](adr/0008-claim-audit-design.md)、[0009](adr/0009-compute-gate-design.md)、[0011](adr/0011-diagnose-experiment-design.md)。原始名單裡的 `run-analysis` 評估後決定不做；`pilot-planning` 與 MLflow adapter 仍明確延後。

生命週期契約與研究資料結構由 [ADR 0013](adr/0013-frontier-research-agent-methodology-evaluation.md) 擁有，P0 與 P1 已實作：

| 部件 | 位置 |
|---|---|
| 研究問題憑證 | `experiment-contract.schema.json` 的 `derivation` |
| 共用 provenance | `provenance.schema.json` 的 `producer`，跨檔 `$ref` |
| 版本化 prompt role | `records/experiments/prompts/<role>@<version>.md`，六個 |
| prompt 輸出型別 | `prompt-output.schema.json`，不含任何閘門或狀態欄位 |
| 失敗分類唯一來源 | `failure-taxonomy.schema.json`，其他 schema 一律 `$ref` |
| 結構化診斷 | `failure-diagnosis.schema.json` → `records/experiments/diagnoses/` |
| 獨立審核包 | `review-package.schema.json` + `review-package` 子命令 |
| 算力階梯 | Contract 的 `compute_cascade`，門檻凍結在 Contract 而非命令列 |
| 貫穿式 fixture | `profiles/experimental/fixtures/rag-walkthrough/`，四條鏈含三條反例 |

P2（第 13–16 項）未動，啟用門檻寫在 ADR 裡。

`viewer/experiment-viewer/` 是 Windows 原生、JSON-only、唯讀的實驗瀏覽器。對外唯一入口 `loadProject(root) -> ProjectSnapshot`，依 `records/experiments/viewer.json` 存不存在自動選 canonical 或 manifest adapter。路徑 containment 在 Rust 端做，不靠 `tauri-plugin-fs` 的 scope。設計見該目錄 README 與 [ADR 0012](adr/0012-experiment-viewer-toolchain.md)。

## Experiment record validator

`profiles/experimental/tools/experiment-records/` 是來源。
`apply.sh --profile experimental` 將它投射到 `.agents/tools/experiment-records/`。
公開 CLI 是 `.agents/tools/experiment-records`。它有四個子命令：

```bash
uv run --project .agents/tools/experiment-records python -m experiment_records validate .
uv run --project .agents/tools/experiment-records python -m experiment_records transition . <EXPERIMENT_ID> <TO_STATE> --reason "<REASON>"
uv run --project .agents/tools/experiment-records python -m experiment_records prompts .
uv run --project .agents/tools/experiment-records python -m experiment_records review-package . <CLAIM_ID> --output <PATH>
```

`validate` 除了 schema 與 project-ref，還做跨檔的確定性檢查：run lineage 不得成環、claim 標 `supported` 必須有結論相符的稽核、稽核者身分必須滿足 Contract 凍結的 `review_policy`、`producer.prompt_hash` 必須對得上 prompt 檔案的實際內容。

`records/experiments/lifecycles/` 每個 JSON 只記一個不可變 transition event。
目前狀態由完整事件序列計算。
`lifecycle-state.schema.json` 擁有 state、合法轉移與 evidence gate。

第三方授權集中在 `docs/THIRD_PARTY_LICENSES.md`。
`apply.sh` 將這個單一文件投射到目標專案。
## 已知限制（新人不知道就會誤判）

- 語意檢索（memsearch）對「用詞接近」有效，對「換完全不同的說法」不可靠。分數 0.5 附近是沒有好答案時的墊底值，不是命中——memsearch 不會說找不到，它照樣回傳最爛的那個。
- `docs/` 與對話記憶的資料量差距很大時，數量多的一方會壓過另一方，使檢索結果與權威順序相反。真的發生時用 `-c` 分開 collection。
- memsearch 預設 embedding provider 是 OpenAI，不設定的話第一次索引會因缺 `OPENAI_API_KEY` 直接失敗。切到本機模型（onnx）首次索引要從 HuggingFace 下載約 558 MB 的 bge-m3 int8 模型，之後快取在 `~/.cache/huggingface/`。
- 索引冷啟動 54–184 秒（波動大，只需一次）；內容不變或只新增一塊重跑約 5 秒，幾乎全是模型載入時間，跟 chunk 數無關——這是預期行為，不是效能退化。
