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

這個技能不判斷「哪個 run 比較好」，只負責觸發並解釋 `compare_runs.py` 的結果。真正的可比較性判定跟指標差異計算是確定性腳本，不是 LLM 自由發揮——同一組 run 兩次比較必須給出同樣結果，而且**不確定的時候不下結論**。

## 用法

```bash
python3 profiles/experimental/skills/compare-runs/compare_runs.py \
  records/experiments/runs/<run-a>.json records/experiments/runs/<run-b>.json
```

加 `--contract <path>` 明確指定 Experiment Contract（預設從 run 的 `experiment_id` 自動找 `records/experiments/definitions/<experiment_id>.json`）。加 `--output <path>` 存一份符合 `comparison-result.schema.json` 的 JSON，給未來的 claim-audit 或 UI 讀。

## 檢查什麼、怎麼判定

1. **兩個 run 是不是同一個實驗**——不是就直接報錯，不比。
2. **可比較性**：讀 Contract 宣告的 `controlled_variables` 跟 `treatment.variable`，載入兩邊 run 的 `config_ref` 實際內容逐欄位比對：
   - `dataset`／`evaluation_set`／`model` 這三個維度固定會檢查，不管有沒有寫進 `controlled_variables`——這幾樣沒道理不一致還能比。
   - `controlled_variables` 宣告的其他欄位也要一致。
   - 宣告的 `treatment.variable` 是唯一允許不同的欄位。
   - 除此之外任何欄位有差異 → 未預期差異。
3. **判定**：任一控制維度 DIFF、或有未預期差異、或宣告變因實際上沒變 → `confounded: true`，`comparison_valid: false`，不計算任何指標差異，也不印「A 優於 B」這類結論。
4. **指標層級**：即使整體可比較，個別指標如果兩邊用的 `metric_definitions` 不一致，那個指標照樣跳過不算——不影響其他指標。
5. 只有整體可比較、指標定義也一致，才算 baseline／treatment／絕對差異／相對差異。

## 讀結果

- exit code 0：可比較（個別指標仍可能因為定義不一致被跳過，看輸出裡的 `未計算` 提示）。
- exit code 1：confounded，`CONFOUNDED COMPARISON` 後面會列出具體理由。看到這個不要接著幫使用者下「哪個比較好」的結論，直接把理由攤開，問要不要修 Contract 或補控制變因後重跑。
- exit code 2：兩個 run 根本不屬於同一個 experiment，或必填欄位缺失——連比都比不了。

## 沒做的事（刻意）

不猜使用者「大概想比什麼」，`config_ref`、`metric_definitions` 缺了就老實說「無法逐欄位比對／無法驗證定義一致」，不假裝可以。不掛 hook 自動在使用者每次問「這個 run 怎麼樣」時觸發——`Comparability Guard` 目前是手動跑，跟這包一貫的「optional 工具不做成 mandatory lifecycle」一致；真的因為忘記跑而反覆出包，再依 Institutionalize Repeated Failures 升格。
