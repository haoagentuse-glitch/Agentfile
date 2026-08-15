---
name: compare-runs
description: >
  Use when comparing two experiment runs, checking if a treatment improved on
  a baseline, or ranking runs. Deterministically checks comparability before
  computing any metric diff — never produces an "A is better than B" claim
  when the comparison is confounded. Triggers on "compare run A to run B",
  "is my run better than baseline", "rank these runs".
metadata:
  source: 部分概念參考 fcakyon/phd-skills@8d642d3e114ee1d1e4d000f918d71e9bf0453dc2 的 compare skill
    （同一 epoch 對齊、代理指標與下游指標分開報這兩條規則），但不是 vendor——這個技能的
    可比較性檢查、confound 判定、輸出 schema 是本包自己設計。取捨依據見 ADR 0007。
---

# Compare Runs

這個技能不判斷「哪個 run 比較好」，只負責觸發並解釋 `experiment_records compare-runs` 的結果。真正的可比較性判定跟指標差異計算是確定性腳本，不是 LLM 自由發揮——同一組 run 兩次比較必須給出同樣結果，而且**不確定的時候不下結論**。

## 用法

```bash
uv run --project .agents/tools/experiment-records python -m experiment_records compare-runs \
  records/experiments/runs/<run-a>.json records/experiments/runs/<run-b>.json
```

加 `--contract <path>` 明確指定 Experiment Contract（預設從 run 的 `experiment_id` 自動找 `records/experiments/definitions/<experiment_id>.json`）。加 `--output <path>` 存一份符合 `comparison-result.schema.json` 的 JSON，給未來的 claim-audit 或 UI 讀——固定慣例存到 `records/experiments/comparisons/<run-a>__<run-b>.json`，例如：

```bash
--output records/experiments/comparisons/<run-a>__<run-b>.json
```

experiment-viewer 只會自動掃描這個固定路徑；存在別處的話 viewer 看不到。

## 檢查什麼、怎麼判定

1. **兩個 run 是不是同一個實驗**——不是就直接報錯，不比。
2. **可比較性**：讀 Contract 宣告的 `controlled_variables` 跟 `treatment.variable`，載入兩邊 run 的 `config_ref` 實際內容逐欄位比對：
   - `dataset`／`evaluation_set`／`model` 這三個維度固定會檢查，不管有沒有寫進 `controlled_variables`——這幾樣沒道理不一致還能比。
   - `controlled_variables` 宣告的其他欄位也要一致。
   - 宣告的 `treatment.variable` 是唯一允許不同的欄位。
   - 除此之外任何欄位有差異 → 未預期差異。
3. **指標層級**：個別指標如果兩邊用的 `metric_definitions` 不一致，那個指標跳過不算——不影響其他指標。
4. 只有整體可引用、指標定義也一致，才算 baseline／treatment／絕對差異／相對差異。

## 三個判斷，分開表示

輸出把可比較性拆成三個獨立布林值，因為它們問的是不同問題：

| 欄位 | 問什麼 | 什麼時候是 false |
|---|---|---|
| `structurally_comparable` | 兩邊在講同一件事嗎 | 沒有任何指標兩邊都存在且定義一致 |
| `controlled_variables_match` | 除了宣告的變因，其他條件真的一樣嗎 | 控制維度 DIFF、有未預期差異，或根本無法逐欄位比對 |
| `confounded` | 差異嚴重到不能歸因嗎 | ——（為 true 時代表不能歸因） |

`comparison_valid` 是綜合結論：非 confounded 且結構可比較。三者都由程式算，不接受 LLM 直接決定。

`differences` 是「什麼不一樣」的唯一清單，每筆帶 `category`（config／data／model／prompt／evaluator／sample／unknown）與 `severity`。宣告的實驗變因也會列在裡面，但 `severity` 是 `informational`、`declared` 為 `true`——那正是實驗要測的東西。

`diagnostic_suggestions` 留給 agent 填異常解釋與下一步建議。它跟 validity 欄位刻意分開：建議永遠不得改變 `comparison_valid` 或 `confounded`。

## 讀結果

- exit code 0：可引用（個別指標仍可能因為定義不一致被跳過，看輸出裡的 `未計算` 提示）。
- exit code 1：不可引用。看 `CONFOUNDED COMPARISON`（條件沒守住）或 `NOT STRUCTURALLY COMPARABLE`（沒有共同基準）後面列的理由。兩者都不要接著幫使用者下「哪個比較好」的結論，直接把理由攤開，問要不要修 Contract、補控制變因或對齊指標定義後重跑。
- exit code 2：兩個 run 根本不屬於同一個 experiment，或必填欄位缺失——連比都比不了。

## 沒做的事（刻意）

不猜使用者「大概想比什麼」，`config_ref`、`metric_definitions` 缺了就老實說「無法逐欄位比對／無法驗證定義一致」，不假裝可以。不掛 hook 自動在使用者每次問「這個 run 怎麼樣」時觸發——`Comparability Guard` 目前是手動跑，跟這包一貫的「optional 工具不做成 mandatory lifecycle」一致；真的因為忘記跑而反覆出包，再依 Institutionalize Repeated Failures 升格。
