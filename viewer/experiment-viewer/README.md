# Experiment Viewer

Windows 原生、完全本機、唯讀的實驗瀏覽器。它把一個 project 的 JSON 實驗紀錄投影成 Overview、experiment workspace、Compare、Records、Artifacts、Claims 與 Diagnostics；不寫回、不刪除、不重跑實驗，也不維護第二份權威資料。

## 啟動

```powershell
experiment-viewer.exe C:\path\to\project
```

直接開啟指定 project；相對路徑以啟動當下的工作目錄解析。不帶參數時顯示資料夾選擇器。

```bash
experiment-viewer.exe "$(wslpath -w "$PWD")"
```

從 WSL 啟動 Windows 程式時，由 shell 把目前目錄轉成 Windows 路徑。程式本身不 hardcode Windows、Linux 或使用者絕對路徑。

可選 project root，也可直接選 `<projectRoot>/records/experiments/`；兩者會解析成同一個 project。正式程式是 Tauri WebView 桌面 app，不啟動 localhost。

## 資料契約

### Canonical records

未提供 manifest 時，Viewer 讀取固定的唯讀目錄慣例：

```text
<projectRoot>/records/experiments/
├── definitions/<experiment_id>.json
├── runs/<run_id>.json
├── comparisons/<run-a>__<run-b>.json
├── claims/<claim_id>.json
├── audits/<claim_id>.json
├── gates/<experiment_id>.json
├── metrics/<metric_name>.json
└── artifacts/                         # 實際 artifact 可位於 projectRoot 內其他相對路徑
```

目錄不存在代表該類資料尚未產生，是空狀態；權限錯誤、路徑跳脫或無法讀取則是錯誤。單一 JSON 壞掉只產生一筆 diagnostic，不阻斷其他檔案。

### Manifest-driven generic JSON

自訂 schema 的 manifest 固定放在：

```text
<projectRoot>/records/experiments/viewer.json
```

manifest 中的 `dir` 全部相對 `<projectRoot>`，不得用絕對路徑或 `..` 跳脫。第一版只支援 JSON 與受限 dot-path；不支援 JSONPath、萬用字元或腳本表達式。

```json
{
  "version": 1,
  "experiments": {
    "dir": "experiments",
    "id": "meta.id",
    "displayName": "meta.title",
    "status": "meta.status"
  },
  "runs": {
    "dir": "runs",
    "id": "meta.id",
    "experimentId": "meta.experiment",
    "status": "meta.status",
    "createdAt": "meta.created_at",
    "metricsPath": "results.metrics",
    "artifactsPath": "results.artifacts"
  },
  "metrics": [
    {
      "name": "accuracy",
      "displayName": "Accuracy",
      "unit": "ratio",
      "format": ".2%",
      "direction": "higher_is_better"
    }
  ],
  "collections": {
    "notes": {
      "dir": "notes",
      "id": "meta.id",
      "columns": ["meta.title", "body"]
    }
  }
}
```

`viewer.json` 不存在時使用 canonical adapter；存在但格式錯誤時顯示 manifest error，不偷偷退回 canonical。缺少 metric direction 時保持中性，不猜 higher/lower-is-better。

## 架構與安全邊界

```text
project path
    ↓
Rust path resolution + containment + read-only I/O
    ↓
loadProject(root) → ProjectSnapshot
    ├── Canonical Records Adapter
    └── Manifest Adapter
    ↓
Vue views / tables / ECharts
```

`loadProject(root) -> ProjectSnapshot` 是 UI 唯一資料入口。Vue 不讀原始 JSON 欄位、不拼 OS path；所有列目錄、讀檔與 artifact path 解析都經 Rust command。Rust 拒絕絕對的相對參數、`..` traversal 與 symlink escape。Viewer 只開啟已存在的 comparison-result，不自行重算比較或改寫判定。

## 資訊架構

- Overview：全部 experiments、run/claim 狀態、有效比較、可信 improvement/regression、最近更新與錯誤摘要。
- Experiments：可篩選、排序的 project experiment 列表。
- Experiment workspace：Summary、Runs、Compare、Records、Artifacts、Claims tabs；單筆細節使用右側 Drawer。
- Records：metric definitions 與 manifest 定義的動態 collections/columns；支援篩選、排序與 group by。
- Diagnostics / About：project/records roots、adapter、path kind 與逐檔錯誤。

Compare 只有在 `comparison_valid=true`、非 confounded，且 metric 明確宣告 direction 時，才標示 improvement/regression。invalid 與 confounded 是不同狀態，均不畫比較圖。

## 開發與驗收

```bash
cd viewer/experiment-viewer && npm ci
```

在 WSL 使用 Linux Node/npm 安裝鎖定依賴，不混用 Windows npm 與 WSL UNC 路徑。

```bash
cd viewer/experiment-viewer && npm test
```

執行 adapter、manifest、dot-path、comparison status 與 project layout 的 Vitest 測試。

```bash
cd viewer/experiment-viewer && npm run build
```

執行 `vue-tsc --noEmit` 與 Vite production build。

```bash
cd viewer/experiment-viewer && cargo test --manifest-path src-tauri/Cargo.toml
```

執行 Rust 路徑 containment、Windows/UNC/WSL UNC 分類與 IPC serialization 測試。

```bash
cd viewer/experiment-viewer && npm run tauri dev
```

啟動開發用 Tauri 視窗；Linux 需 WebKitGTK/GTK 等系統依賴，見 [ADR 0012](../../docs/adr/0012-experiment-viewer-toolchain.md)。

## Windows release

正式 `.exe` 與 installer 必須在 Windows NTFS checkout 建置；不要在 WSL UNC 路徑直接執行 Windows npm/cargo。

```powershell
cd viewer\experiment-viewer; npm ci; npm test; npm run build; cargo test --manifest-path src-tauri\Cargo.toml; npm run tauri build -- --bundles nsis
```

這一行完成乾淨依賴安裝、測試、前端 build、Rust 測試與 unsigned NSIS installer 建置。輸出位於 `src-tauri\target\release\bundle\nsis\`。