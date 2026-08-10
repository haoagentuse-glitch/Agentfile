# experiment-viewer — canonical model 設計

`records/experiments/` 是 experimental profile 的權威來源（見 `profiles/experimental/AGENTS.md` 的 Canonical Records 一節）。這個 viewer 只是消費者，不維護另一份權威副本——讀出來畫圖，不寫回、不快取成第二個真相。

## 四層架構

```
Raw Records (JSON, 依 schemas/*.schema.json)
      │
      ▼
Storage Adapter        ← 決定「資料放哪裡」：本機檔案系統、之後可能是遠端 API
      │
      ▼
Schema Adapter          ← 決定「怎麼解析」：認 schema_version，把已知欄位轉成 canonical 型別
      │
      ▼
Canonical Experiment Model   ← 跟原始 JSON 結構脫鉤的固定 TS 型別，UI 只認這層
      │
      ▼
Viewer（Vue 元件 + ECharts）
```

分四層是因為兩個變動來源要各自隔離：**資料放哪裡**（本機 vs 之後可能的遠端）跟**資料長什麼樣**（schema 版本升級）不該互相牽動，也不該讓 UI 元件直接綁定 JSON 檔案的實體欄位名——schema 加欄位或改名時,只改 Schema Adapter,UI 不用動。

## v1 Walking Skeleton 只做的部分

- **Storage Adapter**：只有一種，讀本機檔案系統的 `records/experiments/{definitions,runs}/`。不做遠端 API adapter——沒有第二個資料來源之前先做抽象是預測性設計,違反 YAGNI。
- **Schema Adapter**：只認目前這包定義的 schema（`experiment-contract` / `run-envelope` / `comparison-result` / `claim` / `claim-audit-result` / `gate-state`,見 `profiles/experimental/records/experiments/schemas/`),依 `schema_version` 挑對應解析邏輯。
- **Canonical Model**：見下方型別定義,直接對應這幾份 schema 目前有的欄位,不預先多加「以後可能需要」的欄位。
- **Viewer**:一個畫面——選一個 experiment,列出底下的 run,選兩個 run 顯示 `compare-runs` 產出的 `comparison-result.json`(指標差異用 ECharts 長條圖,`comparison_valid=false` 時不畫圖只顯示 confounded 原因,不得暗示可比較)。

## 明確不做的部分(YAML manifest mapping,先寫這裡不寫程式)

原規格要求「schema-agnostic,透過 adapter 支援其他實驗紀錄格式」。v1 只有這包自己定義的一種格式,寫一個真正可插拔的 adapter plugin 系統是預測性抽象。等真的出現第二種來源(例如要吃別人專案的 MLflow 匯出、或這包的 schema 大改版又要同時相容舊資料)時,新來源的欄位對應優先用 **YAML manifest** 描述(來源欄位 → canonical 欄位的宣告式映射),不是寫一個新的 TypeScript adapter class:

```yaml
# 未來範例,v1 不存在這個檔案
source: mlflow-export
version: 1
mapping:
  run_id: info.run_id
  status: info.status
  metrics: data.metrics
```

理由:宣告式映射能用 schema 驗證、能被非工程背景的人讀懂改動;寫一支新 adapter class 要重新編譯、重新測試,對「換一種資料來源」這種相對常見的變動來說成本過高。只有 manifest 映射不了的情況(例如來源需要跑一段轉換邏輯,不是單純欄位改名)才落到寫 adapter plugin。

## Canonical Model(TypeScript,對應目前 schema 版本)

```ts
export type RunStatus = "pending" | "running" | "completed" | "invalid";

export interface CanonicalRun {
  runId: string;
  experimentId: string;
  experimentType: string;
  status: RunStatus;
  createdAt: string;
  baselineRun: string | null;
  treatment?: string;
  configHash: string;
  metrics: Record<string, number>;
  invalidReason?: string;
}

export interface CanonicalExperiment {
  experimentId: string;
  question: string;
  hypothesis: string;
  status: "draft" | "locked";
  contractHash?: string;
  primaryMetric: string;
  secondaryMetrics: string[];
  runs: CanonicalRun[];
}

export interface CanonicalMetricDiff {
  metric: string;
  definitionConsistent: boolean;
  computed: boolean;
  baseline: number | null;
  treatment: number | null;
  absoluteDiff: number | null;
  relativeDiff: number | null;
}

export interface CanonicalComparison {
  experimentId: string;
  runA: string;
  runB: string;
  comparisonValid: boolean;
  confounded: boolean;
  confoundedReasons: string[];
  metrics: CanonicalMetricDiff[];
}
```

`comparison_valid=false` 或 `confounded=true` 是一等公民狀態,不是錯誤——UI 一定要能呈現這個狀態本身,不能只在「有效比較」時才有畫面(見 `profiles/experimental/AGENTS.md` 規則 10:混雜比較不得下因果性結論,viewer 不能繞過這條)。

## 技術選型與理由

- **Tauri**:本機優先、免安裝執行環境依賴(不像 Electron 要另外包 Chromium)、跟這包「不需要外掛、複製檔案就能用」的定位一致。
- **Vue + TypeScript**:型別對齊 canonical model,編譯期擋住欄位改名漏改的錯誤。
- **ECharts**:圖表庫夠成熟,不用自己刻畫圖邏輯(Borrow Before Building)。
- 不接 MLflow/W&B 等 tracking 工具——理由與先前 Phase A 的評估一致,`records/` 本身已是權威來源,tracking 工具只會是以後可選的 storage adapter,不是必要依賴。

## 開發

```bash
cd viewer/experiment-viewer
npm install
npm run tauri dev
```

需要本機 Rust 工具鏈(`rustup`)與 Node.js;Linux 端另需 `libwebkit2gtk-4.1-dev` 等系統套件,見 [ADR 0012](../../docs/adr/0012-experiment-viewer-toolchain.md)。
