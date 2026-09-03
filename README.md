# Agentfile

Agentfile 產生可直接複製到專案的 Agent 工作包。複製完成後，檔案就屬於目標專案。執行期不依賴 Agentfile，也不需要安裝紀錄或更新協定。

## 建立發行包

安裝命令列工具：

```bash
uv tool install .
agentfile build
```

在本倉庫開發時，也可直接執行：

```bash
uv run agentfile build
```

命令會依 [agentfile.toml](agentfile.toml) 產生兩個完整目錄：

| 發行包 | 用途 |
|---|---|
| `dist/core-superpowers/` | 一般軟體與文件工作 |
| `dist/experimental/` | 加入研究設計、實驗紀錄、驗證與比較能力 |

`experimental` 在原始碼層繼承 `core-superpowers`。`agentfile build` 會在建置時完成組合。因此，兩個輸出都是獨立且完整的目錄。

## 複製到專案

選一個發行包。把其中內容完整複製到專案根目錄：

```bash
cp -a dist/core-superpowers/. /path/to/project/
```

研究型專案改用：

```bash
cp -a dist/experimental/. /path/to/project/
```

複製後可直接啟動 Claude Code 或 Codex。Claude Code 讀 `.claude/skills/`。Codex 讀 `.agents/skills/`。兩者是內容相同的實體目錄，不使用 symlink。

目標專案可以修改這些檔案。Agentfile 不追蹤目標專案，也不提供上游或下游回報流程。需要新版時，重新建立發行包，再由使用者審查並複製差異。

## 工作方式

`core-superpowers` 使用 vendored [obra/superpowers](https://github.com/obra/superpowers) 工作流。需求先經 `brainstorming` 形成設計。核准後由 `writing-plans` 產生計畫。實作使用測試驅動開發、完成前驗證與程式碼審查。

core 也包含 `frontend-router`。它依框架與頁面類型漸進載入 Streamlit、React／Next.js／shadcn 或 SwiftUI 技能，再按需求加入設計系統、動效與審查技能。Archify 與 Mono Color 不在此路由內。

文件是規格與決策的權威來源：

- `docs/superpowers/specs/` 保存核准的設計。
- `docs/superpowers/plans/` 保存實作計畫。
- `docs/adr/` 保存難以逆轉的架構決策。
- `docs/contracts/` 保存穩定的輸入與輸出契約。

GitHub Issue、對話、記憶與外部 tracker 可以連到文件，但不得取代文件。

## Experimental

`experimental` 在 core 工作流上增加研究型 Agent 的實驗生命週期。它包含：

- 實驗設計、證據審查、比較、claim audit、Compute Gate 與失敗診斷技能。
- `records/experiments/` 的 JSON Schema 與 prompt。
- `.agents/tools/experiment-records/` 的唯一定義與驗證 CLI。

完整 RAG 範例位於 [examples/experimental/rag-walkthrough](examples/experimental/rag-walkthrough/README.md)。Experiment Viewer 是獨立 Windows 原生工具，不會進入任何發行包。操作方式見 [Viewer README](viewer/experiment-viewer/README.md)。

## 倉庫結構

| 路徑 | 職責 |
|---|---|
| `agentfile.toml` | profile、繼承與 layer 的唯一設定來源 |
| `src/agentfile/` | `agentfile build` 實作 |
| `packages/core-superpowers/` | core 來源 layer |
| `packages/experimental/` | experimental 增量 layer |
| `dist/` | 可刪除並重建的完整發行包 |
| `examples/` | 不會進入發行包的範例 |
| `viewer/` | 獨立的 Experiment Viewer |
| `docs/` | Agentfile 本身的架構、契約與決策 |

完整邊界見 [架構文件](docs/architecture.md)。

## 驗證

```bash
uv sync --frozen
uv run --frozen ruff check src tests packages/experimental/.agents/tools/experiment-records/src packages/experimental/.agents/tools/experiment-records/tests
uv run --frozen pytest
uv run --project packages/experimental/.agents/tools/experiment-records --frozen pytest packages/experimental/.agents/tools/experiment-records/tests
```

Viewer 有自己的測試與發行流程。請依 [Viewer README](viewer/experiment-viewer/README.md) 執行。

## 第三方授權

第三方授權請參閱 [docs/THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md)。
