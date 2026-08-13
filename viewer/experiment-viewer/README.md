# Experiment Viewer

Windows 原生、完全本機、唯讀的實驗瀏覽器。開啟一個 project，把裡面的 JSON 實驗紀錄畫成畫面。

它不寫回、不刪除、不重跑實驗，也不重算任何判定——看到的每個結論都來自 `records/` 裡已經存在的檔案。

## 開啟

```powershell
experiment-viewer.exe C:\path\to\project
```

不帶參數會跳資料夾選擇器。指到 project 根目錄或直接指到 `<project>\records\experiments\` 都可以。

從 WSL 啟動時自己轉路徑：

```bash
experiment-viewer.exe "$(wslpath -w "$PWD")"
```

## 怎麼讀畫面

四個地方的規則跟直覺不同，值得先知道：

**比較圖只在可引用時才畫。** `comparison_valid=false` 一律不畫，也不標 improvement/regression。不可引用有兩種原因，畫面上分開顯示：`confounded`（控制條件沒守住）與「沒有共同基準」（兩邊指標定義對不上）。後者不是混雜，別混為一談。

**沒有宣告方向的指標只顯示變化量。** 指標沒定義 higher/lower-is-better 時，Viewer 不猜，只給數字不給好壞。

**失敗不會被藏起來。** 作廢的 run、`refuted` 與 `inconclusive` 的結論都照實列出。Claims 分頁另外顯示失敗診斷，確定性事實與 agent 推測分兩區——分不清這兩者，猜測久了會被當成事實。

**結論可以一路點回去。** 點開任一 claim，Drawer 底部是完整證據鏈：

```text
claim → 稽核 → 比較 → runs → 實驗定義 → 研究問題憑證 → 查過的來源 → prompt 版本
```

接不上的環節會標紅留在鏈上，不會消失。鏈上少一環，跟鏈上有一環接不上，是兩回事。

## 它讀什麼

預設讀這個目錄慣例，缺哪個目錄就是那類資料還沒產生，不是錯誤：

```text
<project>/records/experiments/
├── definitions/   實驗契約（含研究問題憑證）
├── runs/          每次執行
├── comparisons/   比較結果
├── claims/        結論
├── audits/        結論稽核
├── diagnoses/     失敗診斷
├── gates/         算力升級歷史
├── metrics/       指標定義
└── artifacts/
```

單一檔案壞掉只會在 Diagnostics 記一筆，其他檔案照常載入。權限錯誤與路徑跳脫則是錯誤，會明講，不會偽裝成空畫面。

### 自訂 schema

資料不是上面的格式時，放一份 `<project>/records/experiments/viewer.json` 描述欄位對應：

```json
{
  "version": 1,
  "experiments": { "dir": "experiments", "id": "meta.id", "displayName": "meta.title" },
  "runs": { "dir": "runs", "id": "meta.id", "experimentId": "meta.experiment",
            "metricsPath": "results.metrics" },
  "metrics": [{ "name": "accuracy", "format": ".2%", "direction": "higher_is_better" }],
  "collections": { "notes": { "dir": "notes", "id": "meta.id", "columns": ["meta.title", "body"] } }
}
```

`dir` 一律相對 project 根目錄，不接受絕對路徑或 `..`。只支援 JSON 與這種簡單的點號路徑，不支援萬用字元或運算式。

新增欄位只要改這份檔案，不必改程式。`viewer.json` 格式錯誤時會直接說，不會安靜退回預設慣例。

## 安全邊界

所有檔案存取都在 Rust 端做，前端拿不到檔案系統。絕對路徑、`..` 跳脫、指到 project 外的 symlink 一律拒絕。UI 只有一個資料入口 `loadProject(root)`，Vue 不直接讀原始 JSON 欄位，也不自己拼路徑。

## 建置 exe

必須在 Windows 本機 NTFS checkout（不能是 `\\wsl$\...`）：

```powershell
cd viewer\experiment-viewer; npm run release:windows
```

這個指令會裝依賴、跑完前端與 Rust 測試、建置、驗證產物是合法的 Windows 執行檔，最後輸出到 `viewer\experiment-viewer.exe`。任何一步失敗就中止。

exe 不進版控——它隨時可以從原始碼重建，權威來源是 source 加上兩份鎖檔。

## 開發

| 指令 | 做什麼 |
|---|---|
| `npm ci` | 裝鎖定的依賴（在 WSL 用 Linux Node，不混用 Windows npm） |
| `npm test` | Vitest：資料層邏輯 + 掛載元件的 jsdom 測試 |
| `npm run build` | 型別檢查與 production build |
| `cargo test --manifest-path src-tauri/Cargo.toml` | 路徑 containment 與 IPC 契約測試 |
| `npm run tauri dev` | 開發視窗（Linux 需 WebKitGTK，見 [ADR 0012](../../docs/adr/0012-experiment-viewer-toolchain.md)） |

工具鏈與資訊架構的取捨理由都在 [ADR 0012](../../docs/adr/0012-experiment-viewer-toolchain.md)，不在這裡重述。
