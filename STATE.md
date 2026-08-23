now: ADR 0018 的 estimand／estimator／estimate／decision 四層拆分已實作並整合 Viewer；Python 259、Viewer 108、Rust 16、ruff、apply.sh 投影與下游 validate 全通過。
next: 開 PR 併入 main；合併後更新 frus-agentic-rag_v2，移除下游 vendored 的 joint cluster bootstrap workaround 與對應 EXCEPTION。
blocked: Windows 安裝包 gate（`npm run release:windows`）本機跑不了，需要 NTFS checkout。
