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
| `apply.sh` | 依 `--profile` 投射規則、skills、tools、records 與第三方授權文件；已存在檔案一律跳過 | 人工執行，一次性、可重跑 |
| `.memsearch/memory/*.md` | 跨 session 記憶 SSoT，預設本機、不進版控 | memsearch CLI（機器層依賴，見下） |

agentfile 自己的根目錄 `AGENTS.md`／`.gitignore`／`.claude/settings.json`／`.claude/skills` 是手動組裝出跟 `apply.sh --profile software` 相同邏輯的結果——`apply.sh` 拒絕以自己為目標（見 [ADR 0003](adr/0003-apply-copies-not-symlinks-to-dotfiles.md)），所以這四個產物不會自動同步，改了 `core/` 或 `profiles/software/` 底下的來源要記得手動重跑組裝。

## 邊界

- `apply.sh` 只複製檔案與建 symlink，不安裝、不修改使用者層外掛設定——理由見 [ADR 0001](adr/0001-memsearch-two-layer-memory.md)。
- 跨 session 記憶預設不進版控，需要攜帶時使用者手動選擇追蹤——理由見 [ADR 0002](adr/0002-memsearch-memory-not-tracked-by-default.md)。
- `apply.sh` 複製整棵樹進目標專案，不 symlink 指回這包所在的家目錄——理由見 [ADR 0003](adr/0003-apply-copies-not-symlinks-to-dotfiles.md)。改成全域 symlink 是常見的「優化」，但會破壞規範與記憶只隨專案走的前提，改動前先讀這條 ADR。
- `.claude/skills` 與（投影後的）`.agents/skills` 都是 symlink 指回 core／profile 的 `skills/`，不是第二份拷貝；改 skill 只改一處。
- 記憶與文件都要主動策展，不是無限堆積——context 越大越雜，agent 表現越差。`docs/` 只在系統長相改變時才寫（不是每張票都跑），語意索引只收 `docs/`，不收整個對話逐字稿，都是把這個邊界落實成具體規則，而非一次性宣告。
- Graphify 是列為 optional 的未來結構檢索層，v1 未安裝——見 [ADR 0004](adr/0004-graphify-optional-structural-layer.md)。啟用門檻與範圍限制都在那裡，不要因為看到別人在用就直接開。
- 只有 active profile 的規則、skill、設定會出現在目標專案裡；未啟用 profile 的東西實體上不存在，不是靠文件告誡 agent 不要用——理由見 [ADR 0005](adr/0005-core-profile-isolation.md)。`profiles/experimental/` 已有 Walking Skeleton 內容（`evidence-review`／`experiment-design`／`experiment-lint`／`compare-runs`／`claim-audit`／`compute-gate`／`diagnose-experiment` 七個 skill、實驗 schema），前三個的取捨依據見 [ADR 0006](adr/0006-experimental-profile-upstream-evaluation.md)，`compare-runs` 見 [ADR 0007](adr/0007-compare-runs-design.md)，`claim-audit` 見 [ADR 0008](adr/0008-claim-audit-design.md)，`compute-gate` 見 [ADR 0009](adr/0009-compute-gate-design.md)，`diagnose-experiment` 見 [ADR 0011](adr/0011-diagnose-experiment-design.md)。`records/experiments/definitions/`、`records/experiments/runs/` 等使用者資料還不存在——那是用到才建立的東西。Phase C：`Experiment Contract → experiment-lint → Run → compare-runs → claim-audit`，加上橫向管制升級節奏的 `compute-gate`、結果不好先查的 `diagnose-experiment`。原始名單裡的 `run-analysis` 評估後決定不做——單一 run 的結果要看直接讀 run envelope，真的需要比較用 `compare-runs`，出問題用 `diagnose-experiment`，沒有具體痛點證明還缺一個獨立 skill，依 Institutionalize Repeated Failures 不預先做。`pilot-planning`、MLflow adapter 還在明確延後的狀態，見各自的 ADR。`viewer/experiment-viewer/` 是 Windows 原生、JSON-only、唯讀的實驗瀏覽器：Tauri + Vue + TypeScript，對外唯一入口 `loadProject(root)`，回傳 `ProjectSnapshot`，底下依 `records/experiments/viewer.json` 存不存在自動選 canonical records adapter（固定目錄慣例）或 manifest-driven generic JSON adapter（受限 dot-path mapping），跨 project root 的檔案存取（含 artifact path traversal 防護）都在 Rust 端做 containment 檢查，不靠 `tauri-plugin-fs` 的 scope。資訊架構、adapter 設計、測試方式見該目錄 README，工具鏈取捨與早期驗證過程見 [ADR 0012](adr/0012-experiment-viewer-toolchain.md)。Aletheia／FirstResearch／FunSearch・AlphaEvolve 三個前沿科研 agent 方法論已研究並記錄哪些原則未來可能吸收（evidence-review 補雙向證據搜尋、claim-audit 的 scope 判斷要求獨立視角、Experiment Contract 補 `falsifier`／`failure_update_rule` 選填欄位），這輪只記錄不套用，見 [ADR 0013](adr/0013-frontier-research-agent-methodology-evaluation.md)。
- `experiment-lint` 只負責觸發 `.agents/tools/experiment-records` 的 canonical validator。Schema、project-ref、Contract config diff 與 lifecycle event 都由同一個 CLI 驗證。`compare-runs` 仍由 `compare_runs.py` 負責 run 可比較性。`claim-audit` 維持機械檢查與 agent 語意判斷分工。

## Experiment record validator

`profiles/experimental/tools/experiment-records/` 是來源。
`apply.sh --profile experimental` 將它投射到 `.agents/tools/experiment-records/`。
公開 CLI 是 `.agents/tools/experiment-records`。它有兩個子命令：

```bash
uv run --project .agents/tools/experiment-records python -m experiment_records validate .
uv run --project .agents/tools/experiment-records python -m experiment_records transition . <EXPERIMENT_ID> <TO_STATE> --reason "<REASON>"
```

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
