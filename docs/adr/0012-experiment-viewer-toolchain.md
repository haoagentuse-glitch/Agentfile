# ADR 0012：Experiment Viewer 的桌面工具鏈與資料邊界

- 狀態：Accepted
- 日期：2026-08-11

## 背景

`records/experiments/` 已有穩定的實驗 contract、run、comparison、claim/audit、gate 與 metric JSON。現在需要一個不改變研究資料、可在 Windows 日常使用、也能讀取其他 JSON schema 的瀏覽器。

難逆邊界是：正式產品為 Windows 原生程式；project 可能位於 Windows drive、UNC 或 WSL filesystem；資料格式不可綁死單一 schema；Viewer 只能讀取與渲染，不成為新的權威來源。

## 決定

### Tauri + Vue 3 + TypeScript + ECharts

採 Tauri 2 作為 Windows 桌面殼層、Vue 3 + TypeScript 作為 UI、ECharts 作為 Compare 圖表。正式 app 使用內嵌 WebView，不啟動 localhost。ECharts 僅註冊 Bar/Grid/Legend/Tooltip/Canvas，Experiment Workspace 由 router lazy load，避免首頁先載入整個圖表引擎。

沒有建立額外 design system。共用元件只包含實際重複的 DataTable、MetricValue、Drawer、RunSelector 與 NavRail。

### Windows release 與 WSL 開發分離

WSL 開發使用 WSL 原生 Node/npm 與 Rust；不借用 Windows `npm.cmd` 操作 WSL UNC checkout。原因是 Windows `cmd.exe` 的 UNC working-directory 限制會讓命令落到錯誤目錄，且跨 OS 混用工具鏈會模糊實際驗證環境。

正式 `.exe`／unsigned NSIS installer 只在 Windows NTFS checkout build。Windows、UNC、WSL UNC 與相對路徑都屬正式輸入；程式不 hardcode host/user 絕對路徑。從 WSL 呼叫 Windows exe 時，由呼叫端使用 `wslpath -w` 轉換路徑。

### 單一資料入口

UI 只依賴：

```text
loadProject(root) -> ProjectSnapshot
```

`loadProject` 先把 project root 或直接選取的 `records/experiments/` 正規化成同一組 `projectRoot` / `recordsRoot`，再選擇 adapter：

- Canonical Records Adapter：讀取 `<projectRoot>/records/experiments/{definitions,runs,comparisons,claims,audits,gates,metrics}/`。
- Manifest Adapter：讀取 `<projectRoot>/records/experiments/viewer.json`，用受限 dot-path 映射位於 project root 內的 JSON 目錄。

manifest 使用 JSON，不使用 YAML，因為專案既有契約與 fixtures 都是 JSON；這可避免增加第二種 parser。第一版不做 CSV、Parquet、DuckDB 或動態 plugin registry；未來有真實資料需求再增加 adapter。

manifest 未宣告 metric direction 時保持 `undefined`。Viewer 不可用預設值猜 higher/lower-is-better，因為方向會直接影響 improvement/regression 的語意。

### Rust 擁有 filesystem boundary

前端不直接使用 filesystem plugin。列目錄、讀檔、初始 root、layout 正規化與 artifact path 解析全部透過 Rust Tauri commands。

`resolve_within_root` 拒絕：

- 絕對的 relative argument；
- `..` traversal；
- canonicalize 後位於 project root 外的 symlink target。

只有 NotFound 可轉成資料類別的空狀態；權限、I/O、containment 與 serialization 錯誤必須顯示，不能 catch-all 偽裝成空資料。單檔 JSON parse/schema error 則隔離為 diagnostic，讓其他檔案繼續載入。

Rust 的 `ProjectLayout` 以 camelCase 序列化，與 TypeScript IPC contract 對齊；此欄位命名有回歸測試鎖定。

### 固定研究輸出位置

`compare-runs` 與 `claim-audit` 的使用範例固定寫入 `records/experiments/comparisons/` 與 `records/experiments/audits/`。命令仍要求顯式 `--output`，不新增隱藏副作用；Viewer 只掃描既有結果，不自行執行比較或稽核。

### 資訊架構

首頁是單一 project 的 Overview。左側固定導覽 Overview / Experiments / Records / Diagnostics；experiment workspace 使用 Summary / Runs / Compare / Records / Artifacts / Claims tabs；單筆 run、gate history、artifact、claim/evidence 使用右側 Drawer。

Compare 將 `valid`、`confounded`、`invalid non-confounded` 分開顯示。只有 valid 且 metric direction 已宣告時才畫圖與標示 improvement/regression。

## 後果

- Viewer 是資料的唯讀投影；schema、JSON 與產出流程仍是權威來源。
- Windows↔WSL boundary 在 Rust path tests、IPC serialization test 與 Windows NTFS release build 三層驗證。
- 新 JSON schema 優先新增或調整 `viewer.json`；只有受限 mapping 無法表達的格式才新增 adapter。
- 第一版明確不做寫回、實驗執行、帳號、雲端同步、CSV/Parquet/DuckDB、任意 JSONPath 或 plugin framework。
- UI production build、Vitest、Rust tests 與 Windows NSIS build 都是 release 驗收 gate；文件不得用過去某次成功取代當前實跑證據。

## 被拒絕的方案

- 瀏覽器 server + localhost：不符合 Windows 原生、無背景服務的產品需求。
- 前端 filesystem scope：路徑 containment 分散且容易給過寬權限。
- 每種 schema 寫一套 Vue：把資料格式耦合進畫面，新增 schema 必須改 UI。
- 動態 adapter plugin system：JSON-only MVP 沒有足夠案例支持這層複雜度。
- 在 WSL UNC checkout 直接跑 Windows npm/cargo：工具與 working-directory 語意不可靠，不能算 Windows release 驗證。