# Agentfile Core

## 語言

所有自然語言輸出使用繁體中文。採用 `ASD-STE100` 的簡化技術寫作原則。

## 文件優先

文件是規格與決策的唯一權威來源。

- `README.md` 說明安裝、啟動、測試與日常操作。
- `docs/architecture.md` 說明目前的系統邊界與資料流。
- `docs/contracts/` 保存穩定輸入與輸出契約。
- `docs/adr/` 保存難以逆轉的架構決策。
- `docs/superpowers/specs/` 保存已核准的設計。
- `docs/superpowers/plans/` 保存可執行的實作計畫。

GitHub Issue、對話記錄、memory 與外部 tracker 都不是規格來源。它們可以連回文件，但不得取代文件。

## 工作流程

依 `using-superpowers` 選擇適用技能。

1. 創造性工作先使用 `brainstorming`。
2. 架構型工作先寫設計文件並取得使用者核准。
3. 使用 `writing-plans` 建立實作計畫。
4. 實作使用 `test-driven-development`。
5. 宣稱完成前使用 `verification-before-completion`。
6. 合併前使用 `requesting-code-review`。

不得以已移除的舊訪談、Issue 發布或上下游回報流程代替此工作流。

## 工程原則

- KISS 與 YAGNI。
- 每種操作只有一個公開入口。
- 設定、schema、文件與實作各有一個權威來源。
- 衍生產物必須可以刪除後重建。
- 先建立可運作的 walking skeleton。
- 先量測，再最佳化。
- 不吞例外。不把錯誤偽裝成空結果。
- 重大副作用必須明確。
- 完成必須附實跑輸出。

## 專案邊界

專案可以直接修改複製進來的 `AGENTS.md`、`CLAUDE.md`、`.agents/` 與 `.claude/`。這些檔案在複製後屬於該專案。

Agentfile 不保存安裝 manifest。不追蹤來源版本。不提供上游或下游回報協定。需要新版時，由使用者重新複製並自行審查差異。

## 技能入口

`.agents/skills/` 與 `.claude/skills/` 是兩份內容相同的實體目錄。Codex 使用前者。Claude Code 使用後者。不得假設 symlink 可用。
