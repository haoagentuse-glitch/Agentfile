# Agentfile 架構

## 系統邊界

Agentfile 是建置工具，不是目標專案的執行期依賴。它把多個來源 layer 組成完整的發行目錄。使用者把發行目錄複製進目標專案後，Agentfile 不再參與。

```text
agentfile.toml
      │
      ├─ packages/core-superpowers/
      │
      └─ packages/experimental/ ── extends core-superpowers
                         │
                  agentfile build
                         ▼
          dist/core-superpowers/   dist/experimental/
               完整、獨立              完整、獨立
                         │
                         └─ 使用者複製到目標專案
```

繼承只存在於原始碼與建置設定。發行包沒有父層指標、安裝 manifest、來源 revision、更新狀態或回報端點。

## 權威來源

| 內容 | 唯一來源 |
|---|---|
| profile 與 layer 關係 | `agentfile.toml` |
| 建置行為 | `src/agentfile/` |
| core 內容 | `packages/core-superpowers/` |
| experimental 增量 | `packages/experimental/` |
| 建置契約 | `tests/test_build.py` |
| Agentfile 本身的現況 | `docs/architecture.md` |
| 難以逆轉的決策 | `docs/adr/` |

`dist/` 是衍生產物。它不進版控，也不得成為修改來源。

## Layer 契約

每個 layer 的目錄形狀和最終專案相同。一般檔案依相對路徑複製。不同 layer 若提供內容不同的同一路徑，建置立即失敗。內容完全相同時可安全合併。

layer 根目錄可提供 `AGENTS*.md` 與 `CLAUDE*.md` 片段。建置器依繼承順序和檔名順序串接片段，產生單一 `AGENTS.md` 與 `CLAUDE.md`。

`.agents/skills/` 是技能來源。建置器把它實體複製為 `.claude/skills/`。來源 layer 不得自行提供 `.claude/skills/`。這項規則避開 Windows 與 WSL 對 symlink 的差異。

## 建置語意

`agentfile build` 預設建立 `agentfile.toml` 內的全部 profile。`--output` 可指定其他輸出目錄。

每個 profile 先在同一檔案系統的暫存目錄完成。成功後才替換該 profile 的舊輸出。重新建置會清除舊輸出中的殘留檔案，但不影響輸出根目錄的其他內容。

建置結果必須具備以下性質：

- 完整：複製單一 profile 目錄即可使用。
- 確定：相同來源產生逐位元相同的檔案內容。
- 隔離：core 不含 experimental 內容。
- 可檢查：缺 layer、繼承循環與檔案碰撞都會明確失敗。
- 可攜：發行包不含絕對路徑或 symlink。

## 文件與工作流

根目錄文件只治理 Agentfile 本身。發行包內的 `AGENTS.md` 才治理目標專案。兩者不再透過投影或受管前綴同步。

目標專案採文件優先的 superpowers 工作流。核准的設計放在 `docs/superpowers/specs/`。實作計畫放在 `docs/superpowers/plans/`。Issue、對話、記憶與外部 tracker 不是規格來源。

Agentfile 不提供 `apply.sh`、`.agentfile/`、upstream feedback 或 downstream feedback。複製後的檔案由目標專案自行維護。

## Experimental

`packages/experimental/` 只保存相對 core 新增的內容。建置後的 `dist/experimental/` 仍是完整發行包。

實驗資料契約位於 `records/experiments/`。確定性操作位於 `.agents/tools/experiment-records/`。技能只負責流程與語意判斷，不重複實作 schema 驗證、生命週期、比較或 gate 邏輯。

RAG 貫穿範例放在 `examples/experimental/rag-walkthrough/`。範例只供本倉庫測試與說明，不進入發行包。

## Viewer

`viewer/experiment-viewer/` 是獨立、唯讀、JSON-only 的 Windows 原生工具。它不屬於任何 profile，也不由 `agentfile build` 複製。正式 Windows 執行檔與安裝程式必須在 Windows NTFS 環境建置。
