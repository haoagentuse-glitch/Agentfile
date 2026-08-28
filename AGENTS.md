# Agentfile 維護規則

## 語言

所有自然語言輸出使用繁體中文。採用 `ASD-STE100` 的簡化技術寫作原則。一句一意。短句。直接表達。固定術語。

## 文件優先

- `README.md` 是使用入口。
- `docs/architecture.md` 是目前架構的唯一來源。
- `docs/adr/` 保存難以逆轉的決策。
- `agentfile.toml` 是 profile、繼承與 layer 的唯一設定來源。
- Code 與 tests 是實際行為的依據。

Issue、對話、記憶與外部 tracker 不是規格來源。改架構前先更新或新增 ADR。不要在多份文件重複同一事實。

## 開發流程

- 不在 `main` 或 `master` 直接修改。
- 先建立可重現的失敗測試，再修改行為。
- 使用 KISS 與 YAGNI。每個公開操作只有一個入口。
- 不吞例外。不把錯誤偽裝成空結果。
- 宣稱完成前，執行相關測試與完整測試。
- 完成必須附實跑輸出。

## 建置邊界

- 來源只放在 `packages/`。不得手改 `dist/`。
- `core-superpowers` 是完整 core layer。
- `experimental` 只保存相對 core 新增的內容。
- `agentfile build` 必須產生可獨立複製的完整 profile。
- `.agents/skills/` 是技能來源。`.claude/skills/` 由建置器產生實體副本。
- layer 間內容不同的同路徑檔案必須使建置失敗。
- 發行包不得包含 `apply.sh`、`.agentfile/`、安裝狀態或回報協定。

## Vendored 內容

`packages/core-superpowers/.agents/skills/` 內的 superpowers 技能來自固定 commit。除非正在執行明確的 vendor 更新，不要改寫其流程語意。來源與授權記在 `docs/THIRD_PARTY_LICENSES.md`。

## Experimental

實驗 schema 與 prompt 位於 `packages/experimental/records/experiments/`。確定性工具位於 `packages/experimental/.agents/tools/experiment-records/`。技能不得複製工具內的判定邏輯。

範例位於 `examples/`。範例不得混入發行包。

## Viewer

`viewer/experiment-viewer/` 是獨立 Windows 原生工具。`agentfile build` 不得包含 Viewer。Windows 發行檔只能在 Windows NTFS checkout 建立。

## 驗證

根目錄 Python 環境只使用 `pyproject.toml + uv.lock + uv`。完整 Python gate：

```bash
uv run --frozen ruff check src tests packages/experimental/.agents/tools/experiment-records/src packages/experimental/.agents/tools/experiment-records/tests
uv run --frozen pytest
uv run --project packages/experimental/.agents/tools/experiment-records --frozen pytest packages/experimental/.agents/tools/experiment-records/tests
```

Viewer 依其 README 執行獨立測試。
