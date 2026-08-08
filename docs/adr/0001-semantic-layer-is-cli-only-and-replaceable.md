# 語意層只用 CLI，且必須可替換

`docs/` 底下的 markdown 是 durable knowledge 的唯一來源；語意索引是從它衍生、可重建的快取。v1 選 memsearch（MIT，markdown 為 SSoT，Milvus Lite 為 shadow index），但只用它的 CLI，**不裝它的 Claude Code 外掛**。

## Considered Options

memsearch 的外掛會自動擷取每輪對話並寫進 `.memsearch/memory/`。這與 agentkit 的職責直接重疊——session 歷史已經有唯一擁有者，再多一套擷取就是同一件事有兩個來源。外掛也裝在使用者層級，clean checkout 換機就散，違反「執行面」的驗收。

## Consequences

語意層不知道 agentkit 存在，agentkit 也不知道語意層存在。兩者唯一的接軌是「durable knowledge 以 markdown 放在 `docs/`」這個慣例。換掉 memsearch 不需要改 agentkit 一行，也不需要改任何 skill——只要新的工具能索引 markdown 目錄。

代價：`docs/` 以外的東西不進語意索引。

**本段關於對話的部分已被 [ADR 0002](0002-conversation-needs-semantic-retrieval-too.md) 取代。** 原文主張「對話內容不進語意索引，這是刻意的」——實際上當時 `messages` 表根本沒實作，那句是事後替疏漏背書。實測證明字面搜尋涵蓋不足，對話同樣需要語意檢索。本 ADR 的核心決定（語意層只用 CLI、必須可替換）仍然有效。
