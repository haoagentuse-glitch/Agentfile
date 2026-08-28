# apply.sh 複製整棵樹，不 symlink 指回全域 dotfiles

> **狀態：已由 [ADR 0023](0023-build-time-profile-composition.md) 取代。本文僅保留歷史脈絡。**

多數「AI agent 用的 dotfiles」慣例（把 `~/.claude`、skills、記憶檔案 symlink 回一份全域家目錄設定）優化的是機器一致性：每台機器、每個專案都讀同一份設定，改一次全部生效。這包刻意不採這個模式。

`apply.sh` 把 `skills/`、`.claude/`、`AGENTS.md` 等整棵樹複製進目標專案，複製後即與這包本身脫鉤。理由是 AGENTS.md「執行面」的不變量：「丟掉 scrollback、換一台機器、clean checkout，能否原樣再做一次」。全域 symlink 模式會讓每個專案隱性依賴使用者家目錄的設定——換一台沒裝這包的機器，clone 下來的專案就讀不到規範與技能。複製讓規範、技能、記憶都只隨專案本身走，不隨開發者的機器走。

## Consequences

- 代價：這包更新後，既有專案不會自動跟著改；要拿到更新得重跑 `apply.sh`。這是刻意的——更新是明確、可審查的一次性動作，不是隱性自動同步。重跑時哪些檔可以安全覆寫、哪些要人工處理，由投影雜湊判定，見 [ADR 0014](0014-apply-manifest-based-update.md)。
- 好處：clone 這包套用過的專案的人，不需要也裝一份 `agentfile` 才能讓 Claude Code、Codex 讀到規範與技能。
- `.claude/skills`、`.agents/skills` 兩個 symlink 不算例外——它們指回同一次複製進來的 `skills/`，是專案內部的路徑折疊，不是指回外部家目錄。
- 需要記憶跨機器帶著走時（見 [ADR 0002](0002-memsearch-memory-not-tracked-by-default.md)），走的是「跟著這個 repo 進版控」的路徑，不是「跟著使用者的家目錄」的路徑——兩種可攜性方向不同，這包只做前者。
