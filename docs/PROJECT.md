# agentfile

**目的**：一套可搬移的開發規範與工作流程。套進任何新專案，讓 Claude Code 與 Codex 遵循同一組規則、讀同一份 skill。

**範圍**：規範文件（`core/AGENTS.md` + `profiles/<name>/AGENTS.md`）、vendored 與自有 skills、`.claude/` 設定、`apply.sh` 投影腳本。分 core（跨專案類型都成立）與 profile（`software`／`experimental`，只在被選為 active profile 時生效）兩層，避免軟體開發規則污染實驗型專案，反之亦然。這包只管「怎麼做事」，不管「做什麼」——不含任何目標專案的業務邏輯。

**穩定背景**：套用方式與每日流程見 [README.md](../README.md)；系統組成見 [architecture.md](architecture.md)；決策理由見 `docs/adr/`；做事規則見 [AGENTS.md](../AGENTS.md)。
