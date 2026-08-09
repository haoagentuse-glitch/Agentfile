# agentfile — 架構

## 部件

| 部件 | 做什麼 | 誰讀它 |
|---|---|---|
| `AGENTS.md` | 規範唯一來源，`CLAUDE.md` 只引用一行 | 每個 agent session 開頭 |
| `skills/<name>/` | 技能 canonical source | `.claude/skills` symlink 指過去；投影後目標專案的 `.agents/skills/` 也指過去 |
| `.claude/` | Claude Code 設定與 command | Claude Code |
| `apply.sh` | 把整包投影到目標資料夾，已存在檔案一律跳過 | 人工執行，一次性、可重跑 |
| `.memsearch/memory/*.md` | 跨 session 記憶 SSoT，預設本機、不進版控 | memsearch CLI（機器層依賴，見下） |

## 邊界

- `apply.sh` 只複製檔案與建 symlink，不安裝、不修改使用者層外掛設定——理由見 [ADR 0001](adr/0001-memsearch-two-layer-memory.md)。
- 跨 session 記憶預設不進版控，需要攜帶時使用者手動選擇追蹤——理由見 [ADR 0002](adr/0002-memsearch-memory-not-tracked-by-default.md)。
- `apply.sh` 複製整棵樹進目標專案，不 symlink 指回這包所在的家目錄——理由見 [ADR 0003](adr/0003-apply-copies-not-symlinks-to-dotfiles.md)。改成全域 symlink 是常見的「優化」，但會破壞規範與記憶只隨專案走的前提，改動前先讀這條 ADR。
- `.claude/skills` 與（投影後的）`.agents/skills` 都是 symlink 指回 `skills/`，不是第二份拷貝；改 skill 只改一處。
- 記憶與文件都要主動策展，不是無限堆積——context 越大越雜，agent 表現越差。`docs/` 只在系統長相改變時才寫（不是每張票都跑），語意索引只收 `docs/`，不收整個對話逐字稿，都是把這個邊界落實成具體規則，而非一次性宣告。

## 已知限制（新人不知道就會誤判）

- 語意檢索（memsearch）對「用詞接近」有效，對「換完全不同的說法」不可靠。分數 0.5 附近是沒有好答案時的墊底值，不是命中——memsearch 不會說找不到，它照樣回傳最爛的那個。
- `docs/` 與對話記憶的資料量差距很大時，數量多的一方會壓過另一方，使檢索結果與權威順序相反。真的發生時用 `-c` 分開 collection。
- memsearch 預設 embedding provider 是 OpenAI，不設定的話第一次索引會因缺 `OPENAI_API_KEY` 直接失敗。切到本機模型（onnx）首次索引要從 HuggingFace 下載約 558 MB 的 bge-m3 int8 模型，之後快取在 `~/.cache/huggingface/`。
- 索引冷啟動 54–184 秒（波動大，只需一次）；內容不變或只新增一塊重跑約 5 秒，幾乎全是模型載入時間，跟 chunk 數無關——這是預期行為，不是效能退化。
