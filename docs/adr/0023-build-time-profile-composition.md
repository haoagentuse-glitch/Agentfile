# 建置時組合完整 Agentfile 發行包

狀態：Accepted

日期：2026-08-28

取代：ADR 0001、0002、0003、0004、0005、0014、0015、0020 與 0022 中和舊投影架構衝突的部分。

## 背景

舊架構用 `apply.sh` 把 core 與單一 profile 投影到目標專案。它同時管理安裝 manifest、更新雜湊、下游修改、來源 revision 與上游回報。這使「把一組 Agent 檔案複製進專案」變成有狀態的同步系統。

實際使用需求更簡單。使用者需要一個可直接複製的完整目錄。複製後的檔案應屬於目標專案。目標專案不應依賴 Agentfile 的位置、版本或更新服務。

一般軟體工作流也已由 superpowers 提供較完整的設計、計畫、測試、驗證與審查流程。繼續維護 `grill-me`、Issue spec 與回報流程會形成第二套生命週期。

## 決定

### 唯一建置入口是 `agentfile build`

`agentfile.toml` 宣告 profile、繼承與來源 layer。`agentfile build` 產生 `dist/core-superpowers/` 與 `dist/experimental/`。

`experimental` 在原始碼層繼承 `core-superpowers`。繼承在建置時解析。發行包沒有執行期繼承。每個輸出都是完整且可獨立複製的目錄。

### Layer 使用最終目錄形狀

一般檔案依相對路徑合併。內容不同的同路徑檔案視為設計碰撞，建置失敗。`AGENTS*.md` 與 `CLAUDE*.md` 是唯一具有串接語意的片段。

`.agents/skills/` 是技能來源。建置器產生內容相同的 `.claude/skills/` 實體副本。不得依賴 symlink。這讓同一發行包可跨 Windows、WSL、Linux 與 macOS 複製。

### 複製是所有權轉移

使用者把發行包複製進專案後，可以直接修改。Agentfile 不寫 `.agentfile/`。它不保存來源 revision、安裝 manifest 或受管檔案清單。它不提供 update、apply、upstream feedback 或 downstream feedback。

需要新版時，使用者重新執行 build，審查差異，再自行複製。這是明確的人工作業，不是自動同步協定。

### 文件優先並採用 superpowers

核准的設計放在 `docs/superpowers/specs/`。實作計畫放在 `docs/superpowers/plans/`。架構決策放在 `docs/adr/`。Issue、對話、記憶與外部 tracker 不是規格來源。

core vendor 固定版本的 `obra/superpowers` 技能。技能保留上游原文，以降低自行改寫造成的語意漂移。Agentfile 的中文輸出與專案規則由額外的 `AGENTS` 片段定義。

舊 software profile、`grill-me` 系列、`to-spec`、`to-tickets`、舊的 implement／TDD／review 技能與回報技能移除。superpowers 取代其軟體生命週期職責。

### Agentfile 本身與發行內容分離

根目錄 `README.md`、`AGENTS.md` 與 `docs/` 只治理 Agentfile 本身。可發行內容只放在 `packages/`。`dist/` 是可刪除並重建的衍生產物。

RAG fixture 移到 `examples/`。Experiment Viewer 保持獨立 Windows 原生工具。兩者都不進入 profile 發行包。

### memsearch 不再是正式元件

Agentfile 不安裝、設定、忽略或規範 memsearch。目標專案可自行選擇記憶工具，但它不是發行契約，也不是文件權威來源。

## 後果

- 使用者只需理解 build 與 copy。
- 發行包可以離線使用，也不依賴 Agentfile 倉庫。
- core 與 experimental 的重複檔案由 build 產生，不由人維護。
- 更新不再自動保留目標專案修改。使用者必須審查複製差異。
- `.agents/skills/` 與 `.claude/skills/` 會占用兩份空間。這是換取跨平台可攜性的刻意成本。
- 歷史 ADR 保留，供理解舊設計。它們不再描述目前契約。

## 被拒絕的方案

### 保留 `apply.sh`，只簡化旗標

拒絕。只要工具仍追蹤目標專案狀態，就必須定義覆寫、衝突、刪除、版本與回復語意。複雜度不會因為少幾個旗標而消失。

### 讓 experimental 在目標專案執行期引用 core

拒絕。它會讓專案依賴 Agentfile 的外部位置，也會重新引入版本配對與路徑邊界問題。

### 只產生 `.agents/skills/`，讓 Claude 使用 symlink

拒絕。Windows 建立與保存 symlink 的條件不一致。完整實體目錄較大，但行為穩定。

### 保留上下游回報作為選用能力

拒絕。回報通道會重新建立來源身分、版本與生命週期協定。一般專案自己的 Issue 或文件已可承載意見，不需要 Agentfile 專用協定。

## 預登記的改判條件

- 發行包大到雙份技能目錄造成可量測的交付問題，且 Windows 原生 directory junction 已能在所有支援環境穩定建立與保存。
- 三個以上目標專案反覆因人工更新遺漏安全修正，且可用無狀態的差異工具解決。
- 第二個以上 profile 出現無法用相同 layer 碰撞規則表達的合法覆寫需求。
