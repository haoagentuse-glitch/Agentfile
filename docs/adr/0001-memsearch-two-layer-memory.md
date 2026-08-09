# 跨 session 記憶：專案層與機器層分兩層，機器層不隨包走

跨 session 記憶原本自建 agentkit（SQLite + LIKE + Markdown export）想記錄多代理的 session 歷史，但這重造了 memsearch 已有的摘要 → memory Markdown → embedding/BM25/RRF → recall pipeline。實測 memsearch 增量索引僅約 5 秒、冷啟動 54–184 秒且只需一次，CPU 足夠應付，因此刪除 agentkit，跨 session 記憶交還 memsearch 原生流程。

進一步把記憶拆成兩層：`.memsearch/memory/*.md` 是可攜的記憶 SSoT，跟著 repo 進版控；memsearch CLI、embedding 模型、各 agent 的官方整合（Claude Code 外掛、Codex hook）屬機器層外部依賴，`apply.sh` 不攜帶也不修改使用者層設定，只檢查並提示安裝方式。理由：外掛裝在使用者層級，clean checkout 換機就散，違反「執行面」的可具名重現驗收；而 memory 的 markdown 本身該跟著專案走，不該綁在特定機器上。

## Consequences

- 換掉 memsearch 不需要改這包任何一行——接軌只是「markdown 放 `.memsearch/memory/`」這個慣例。
- `.gitignore` 只能忽略衍生資料（Milvus 索引、模型快取），不可整個忽略 `.memsearch/`，否則會把可攜 SSoT 一併排除——過去踩過這個坑，已在同一次改動修掉。
- 已知限制與部件關係見 [architecture.md](../architecture.md)。
