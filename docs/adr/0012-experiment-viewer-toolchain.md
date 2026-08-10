# experiment-viewer：Tauri + Vue + TypeScript + ECharts，四層 adapter 架構

`viewer/experiment-viewer/` 是先前 Phase A~C 一路延後的 UI/viewer，等到 `records/experiments/` 的六個 skill 跟七份 schema 都穩定之後才動手——理由跟先前每次延後時寫的一樣：資料層不穩之前先蓋 UI 是本末倒置。這份 ADR 記兩件事：工具鏈怎麼裝、canonical model 為什麼分四層。設計本身的完整說明在 `viewer/experiment-viewer/README.md`,這裡只記取捨過程跟這裡沒重複的部分。

## 工具鏈:改裝 WSL 原生,不借 Windows 那份

一開始想借用 Windows 側已經裝好的 `cargo`(`C:\Users\user\.cargo\bin`)跟 `node`(`v24.18.0`),透過 WSL 的 `/mnt/c/` 互通路徑直接呼叫,省一次安裝。實測發現摩擦比預期大:`node.exe` 可以直接執行,但 `npm.cmd` 是批次檔不是原生執行檔,WSL 的 bash 呼叫不動；改用 `cmd.exe /c npm ...` 又卡在 `cmd.exe` 連不到 `\\wsl.localhost\...` 這個 UNC 路徑,agentfile repo 本身就在 WSL 檔案系統裡,等於死路。

改成在 WSL 內裝原生工具鏈:`rustup`(官方 `sh.rustup.rs` 腳本,裝進 `~/.cargo`)跟 `nvm` + Node LTS(裝進 `~/.nvm`)。這樣跟這包其餘工具鏈(git、python、memsearch)的安裝方式一致——全部原生跑在 WSL 裡,不跨 Windows/WSL 邊界。多花一次安裝時間,換來的是不用每次開發都繞路徑轉換問題。

Linux 端另外需要 `libwebkit2gtk-4.1-dev`、`libgtk-3-dev`、`libayatana-appindicator3-dev`、`librsvg2-dev`、`patchelf`、`build-essential` 這幾個系統套件才能真正編譯執行——這幾個套件要 `sudo`,而這個環境的 `sudo` 需要互動輸入密碼,agent 沒有 TTY 可以輸入,所以這一步交給使用者自己在終端機跑。

## 為什麼做成四層(Storage → Schema → Canonical → Viewer)

原始需求要求「schema-agnostic,透過 adapter 支援其他格式」。這包目前只有自己定義的一種 schema,真的做一套可插拔的 adapter plugin 系統(動態載入、外部註冊)是預測性抽象,先寫死一份 Schema Adapter,只在「資料放哪裡」(Storage)跟「資料長什麼樣」(Schema)兩個維度上留分層邊界,不做成外掛系統。以後真的出現第二種資料來源,優先用 YAML manifest 做欄位對應(宣告式,不用重新編譯),而不是每次寫一個新的 TypeScript class——這個決定跟理由寫在 README,不是這裡重複的部分。

`CanonicalRun`／`CanonicalExperiment`／`CanonicalComparison` 三個型別直接對應 `run-envelope`／`experiment-contract`／`comparison-result` 三份 schema 目前有的欄位,沒有多加「以後可能用到」的欄位。`claim`／`claim-audit-result`／`gate-state` 三份 schema 第一輪沒做對應畫面,第二輪(見下方「補做的部分」)補上——不是回頭違反 YAGNI,是使用者明確要求擴充,不是我自己預先猜的。

## comparison-result 沒有固定目錄慣例,所以是單檔挑選

`experiment-contract` 固定在 `definitions/<id>.json`,`run-envelope` 固定在 `runs/<id>.json`,但 `compare_runs.py` 的輸出路徑是 `--output` 自訂,沒有強制慣例。Storage Adapter 對前兩者做資料夾掃描,對 comparison-result 是讓使用者透過 Tauri 的檔案選擇對話框自己指一個檔案——不是偷懶少做,是如實反映現有腳本本來就沒有固定輸出路徑這件事,UI 不該假裝有。

## 已經驗證、還沒驗證的部分

**已驗證(實際執行過,不是聲稱)**:
- `npx vue-tsc --noEmit` 跟 `npm run build` 都乾淨通過(純前端 build,不需要 Rust/webkit)。
- Schema Adapter(`src/lib/schema-adapter.ts`)的三個轉換函式,對著**真實跑出來的資料**做過測試:用 `compare_runs.py` 實際跑一組 fixture run(baseline `recall_at_10=0.72` vs treatment `recall_at_10=0.79`,`top_k` 為宣告變因,其餘控制維度一致)產生真實的 `comparison-result.json`,再用 Node 的 `--experimental-strip-types` 直接跑 TS 測試腳本驗證 canonical 物件的數字、狀態跟原始腳本輸出完全對得上,包括缺必填欄位時正確丟出 `SchemaAdapterError`——不是手造一份符合預期的假資料倒著寫測試。

**已驗證(系統套件裝好之後,第二輪)**:
- `npm run tauri build -- --debug` 從乾淨狀態實際編譯成功(約 1 分半,含 `deb`／`rpm`／`AppImage` 三種打包產物),過程中抓到並修掉一個真實錯誤:`tauri.conf.json` 的 bundle identifier 原本帶底線(`com.haoche_nitro_v15.experiment-viewer-app`),Tauri 的 bundle identifier 規則只准英數字、連字號、句點,改成 `com.agentfile.experiment-viewer` 才過。
- 編出來的二進位檔(`src-tauri/target/debug/experiment-viewer-app`)在 WSLg(`DISPLAY=:0`)底下實際啟動,`ps` 確認程序存活、沒有立刻崩潰;`xlsclients -a` 確認它註冊成一個真正的 X client;`xwininfo -root -tree` 進一步確認視窗內容裡真的出現 App.vue 寫的按鈕文字「選 records/experiments/ 資料夾」——不是空白視窗或 webview 初始化失敗,是實際渲染出這個畫面的內容。順手把 `index.html` 殘留的 scaffold 預設標題("Tauri + Vue + Typescript App")改成 `experiment-viewer`。

**已由使用者親手驗證(這個環境沒有自動化 GUI 操作工具,無法用腳本模擬點擊)**:
- 跑 `npm run tauri dev`,點「選 records/experiments/ 資料夾」指向這輪產生的真實 fixture,點「選 comparison-result.json」讀 `compare_runs.py` 實際跑出來的比較結果——使用者確認看得到畫面。`src-tauri/capabilities/default.json` 裡的 `fs:scope` 權限範圍(`$HOME/**`、`/**`)也隨這次操作一併驗證過,folder picker 選到的路徑讀得到,沒有被權限擋下來。

## Consequences

- `viewer/experiment-viewer/` 從 canonical model 設計、Schema Adapter 邏輯、型別檢查、實際編譯、視窗啟動渲染,到選資料夾／選比較結果的完整互動路徑,都已經過驗證(部分由 agent 自動執行,互動這段由使用者親手確認)——Walking Skeleton 第一輪算完整走完一次端到端。
- MLflow adapter 還是明確不做的範圍。

## 補做的部分:claim／gate-state 畫面

第一輪刻意不做 `claim`／`claim-audit-result`／`gate-state` 三份 schema 的畫面,理由是「沒有具體畫面需求就不預先加」。這輪使用者明確選擇擴充這塊,於是補上:

- `CanonicalClaim`／`CanonicalClaimAuditResult`／`CanonicalGateState` 三個型別,對應方式跟第一輪的三個型別一致——直接照 schema 現有欄位定,不多加。
- Storage Adapter 新增 `claims/<claim_id>.json`（claim 輸入,固定目錄慣例,跟 `definitions/`／`runs/` 一樣掃資料夾)與 `gates/<experiment_id>.json`（gate state,同樣固定目錄慣例,一個 experiment 一份)兩種讀取路徑;`claim-audit-result.json` 跟 `comparison-result.json` 一樣沒有固定輸出路徑,維持單檔挑選。
- 測試方式跟第一輪一致:用 `claim_audit.py`／`compute_gate.py` 實際跑出真實的 `claim-audit-result.json`（含機械段自動判定跟 agent 補的語意段 `scope_verdict`)與 `gate-state.json`（L0→L1→L2 三筆真實升級歷史,`run_ids` 帶真實 run_id),再用同一支 Node 測試腳本驗證 canonical 物件正確,新增 7 個斷言全部通過。
- 過程中發現一個值得記的細節:`claim_audit.py` 機械段跑完、agent 還沒填語意段之前,`final_verdict` 欄位的值是 `"pending"`——但 `claim-audit-result.schema.json` 的 `final_verdict` enum 並不包含 `"pending"`(只有 `scope_verdict` 允許)。這代表機械段剛跑完、語意段還沒補上的那份檔案,嚴格來說**還不是** schema-valid 的終態,是 claim-audit 技能流程裡刻意存在的中繼狀態(SKILL.md 講得很清楚:機械段過了要「換你判斷」,不是直接可用)。Schema Adapter 沒有加執行期 enum 檢查去擋這個中繼狀態——驗證 schema 合不合法是 `experiment-lint` 的職責範圍,不該在 viewer 裡重做一份,這裡維持只做「讀不讀得出來」的檢查,讀到不合法的終態值也不會噴錯,只會忠實顯示出來。

編譯與視窗渲染驗證跟第一輪同樣的方式又走了一次(`npm run tauri build -- --debug --no-bundle`,`xwininfo` 確認新視窗啟動不崩潰),互動點擊部分留給使用者用這輪新增的 claims／gate-state fixture 親手確認。
