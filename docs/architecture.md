# agentfile — 架構

## 部件

| 部件 | 做什麼 | 誰讀它 |
|---|---|---|
| `core/AGENTS.md` | 跨 profile 都成立的不變量，唯一規範來源的 upstream 部分 | `apply.sh` 串接進目標專案的 `AGENTS.md` |
| `profiles/<name>/AGENTS.md` | active profile 特化規則，追加於 core 之後 | 同上，只有 active profile 那份會被串接 |
| `core/skills/<name>/`、`profiles/<name>/skills/<name>/` | 技能 canonical source，依 core／profile 分層 | `apply.sh` 聯集複製進目標的 `.agents/skills/` |
| `core/.claude/`、`profiles/<name>/.claude/` | Claude Code 設定與 command 的 core／profile 來源 | `apply.sh` 合併（`settings.json` 用 `jq`，其餘用檔案聯集）|
| `profiles/<name>/records/` | 該 profile 擁有的權威 schema（例如 experimental 的實驗、run、指標三份 schema） | `apply.sh` 複製進目標的 `records/`；`definitions/`／`runs/` 這類使用者產生的內容不預建，用到才生 |
| `apply.sh` | 依 `--profile` 把 core + active profile 組裝進目標資料夾，已存在檔案一律跳過 | 人工執行，一次性、可重跑 |
| `.memsearch/memory/*.md` | 跨 session 記憶 SSoT，預設本機、不進版控 | memsearch CLI（機器層依賴，見下） |

agentfile 自己的根目錄 `AGENTS.md`／`.gitignore`／`.claude/settings.json`／`.claude/skills` 是手動組裝出跟 `apply.sh --profile software` 相同邏輯的結果——`apply.sh` 拒絕以自己為目標（見 [ADR 0003](adr/0003-apply-copies-not-symlinks-to-dotfiles.md)），所以這四個產物不會自動同步，改了 `core/` 或 `profiles/software/` 底下的來源要記得手動重跑組裝。

## 邊界

- `apply.sh` 只複製檔案與建 symlink，不安裝、不修改使用者層外掛設定——理由見 [ADR 0001](adr/0001-memsearch-two-layer-memory.md)。
- 跨 session 記憶預設不進版控，需要攜帶時使用者手動選擇追蹤——理由見 [ADR 0002](adr/0002-memsearch-memory-not-tracked-by-default.md)。
- `apply.sh` 複製整棵樹進目標專案，不 symlink 指回這包所在的家目錄——理由見 [ADR 0003](adr/0003-apply-copies-not-symlinks-to-dotfiles.md)。改成全域 symlink 是常見的「優化」，但會破壞規範與記憶只隨專案走的前提，改動前先讀這條 ADR。
- `.claude/skills` 與（投影後的）`.agents/skills` 都是 symlink 指回 core／profile 的 `skills/`，不是第二份拷貝；改 skill 只改一處。
- 記憶與文件都要主動策展，不是無限堆積——context 越大越雜，agent 表現越差。`docs/` 只在系統長相改變時才寫（不是每張票都跑），語意索引只收 `docs/`，不收整個對話逐字稿，都是把這個邊界落實成具體規則，而非一次性宣告。
- Graphify 是列為 optional 的未來結構檢索層，v1 未安裝——見 [ADR 0004](adr/0004-graphify-optional-structural-layer.md)。啟用門檻與範圍限制都在那裡，不要因為看到別人在用就直接開。
- 只有 active profile 的規則、skill、設定會出現在目標專案裡；未啟用 profile 的東西實體上不存在，不是靠文件告誡 agent 不要用——理由見 [ADR 0005](adr/0005-core-profile-isolation.md)。`profiles/experimental/` 已有 Walking Skeleton 內容（`evidence-review`／`experiment-design`／`experiment-lint`／`compare-runs`／`claim-audit`／`compute-gate`／`diagnose-experiment` 七個 skill、實驗 schema），前三個的取捨依據見 [ADR 0006](adr/0006-experimental-profile-upstream-evaluation.md)，`compare-runs` 見 [ADR 0007](adr/0007-compare-runs-design.md)，`claim-audit` 見 [ADR 0008](adr/0008-claim-audit-design.md)，`compute-gate` 見 [ADR 0009](adr/0009-compute-gate-design.md)，`diagnose-experiment` 見 [ADR 0011](adr/0011-diagnose-experiment-design.md)。`records/experiments/definitions/`、`records/experiments/runs/` 等使用者資料還不存在——那是用到才建立的東西。Phase C：`Experiment Contract → experiment-lint → Run → compare-runs → claim-audit`，加上橫向管制升級節奏的 `compute-gate`、結果不好先查的 `diagnose-experiment`。原始名單裡的 `run-analysis` 評估後決定不做——單一 run 的結果要看直接讀 run envelope，真的需要比較用 `compare-runs`，出問題用 `diagnose-experiment`，沒有具體痛點證明還缺一個獨立 skill，依 Institutionalize Repeated Failures 不預先做。`pilot-planning`、MLflow adapter 還在明確延後的狀態，見各自的 ADR。`viewer/experiment-viewer/` 已起手：Tauri + Vue + TypeScript + ECharts，四層 canonical model（Storage Adapter → Schema Adapter → Canonical Model → Viewer）設計見該目錄 README，工具鏈取捨與目前驗證狀態（Schema Adapter 邏輯已對真實 `compare_runs.py` 輸出測試過，GUI 實機執行卡在系統套件安裝、待補測）見 [ADR 0012](adr/0012-experiment-viewer-toolchain.md)。
- `experiment-lint`、`compare-runs` 的檢查邏輯都是確定性腳本（`experiment_lint.py`、`compare_runs.py`），不是純 prompt——能機械判定的規則（必填欄位、baseline/treatment 有沒有未宣告差異、可比較性）不交給 LLM 自由判斷，同樣的輸入兩次檢查必須給出同樣結果。`claim-audit` 是唯一混合式的：`claim_audit.py` 機械判定引用是否存在、有沒有 confounded、數字方向對不對；「結論有沒有超出證據範圍」這種沒辦法寫成規則的語意判斷，才交給呼叫的 agent，兩段分工寫在 ADR 0008，不是偷懶少判定。

## 已知限制（新人不知道就會誤判）

- 語意檢索（memsearch）對「用詞接近」有效，對「換完全不同的說法」不可靠。分數 0.5 附近是沒有好答案時的墊底值，不是命中——memsearch 不會說找不到，它照樣回傳最爛的那個。
- `docs/` 與對話記憶的資料量差距很大時，數量多的一方會壓過另一方，使檢索結果與權威順序相反。真的發生時用 `-c` 分開 collection。
- memsearch 預設 embedding provider 是 OpenAI，不設定的話第一次索引會因缺 `OPENAI_API_KEY` 直接失敗。切到本機模型（onnx）首次索引要從 HuggingFace 下載約 558 MB 的 bge-m3 int8 模型，之後快取在 `~/.cache/huggingface/`。
- 索引冷啟動 54–184 秒（波動大，只需一次）；內容不變或只新增一塊重跑約 5 秒，幾乎全是模型載入時間，跟 chunk 數無關——這是預期行為，不是效能退化。
