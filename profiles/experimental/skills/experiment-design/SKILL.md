---
name: experiment-design
description: >
  Use when the user wants to design experiments, plan ablation studies,
  structure baselines, or create incremental evaluation strategies.
  Triggers on phrases like "design ablation", "plan experiment",
  "what experiments should I run", "baseline comparison", or
  "experiment matrix".
metadata:
  source: fcakyon/phd-skills@8d642d3e114ee1d1e4d000f918d71e9bf0453dc2 (adapted, not verbatim — Step 1-5 與 Verification Checkpoints 取自上游，Step 6-7／Output Format 改為輸出 Experiment Contract 檔案並串 experiment-lint，見 ADR 0006)
  license: MIT
---

# Experiment Design Methodology

You are helping a researcher design rigorous experiments. Follow this methodology systematically.

## Step 1: Understand the Research Question

Before designing any experiment:
- Ask what specific hypothesis or claim the experiment should support
- Identify the dependent variable (metric) and independent variables (factors)
- Clarify the baseline: what is the current best result or default configuration?
- 若這是演算法／架構／retrieval 策略等重大選型，先跑過 `evidence-review`，不要跳過 Research Gate 直接設計實驗。

## Step 2: Single-Variable Isolation

Every ablation study must change exactly ONE variable at a time. For each factor:

1. **Define the factor** — what is being varied (e.g., loss function, learning rate, architecture component)
2. **List levels** — all values this factor will take (e.g., CE, focal, VAR)
3. **Fix everything else** — document what stays constant (seed, data split, epochs, hardware) → this becomes `controlled_variables` in the Contract
4. **Predict outcome** — before running, state what you expect and why

多因素研究要在 Contract 裡明講是多因素設計，不能事後才承認改了不只一個變因。

## Step 3: Experiment Matrix

For multi-factor studies, use a structured matrix:

1. **Full factorial** — if factors are few (≤3) and levels are few (≤3 each)
2. **Sequential elimination** — if factors are many: run single-factor ablations first, then combine winners
3. **Latin square** — if full factorial is too expensive: sample representative combinations

Always calculate total runs before committing:
```
Total runs = product of all factor levels
Compute hours = total runs × hours_per_run
```

## Step 4: Resource Estimation → compute_budget

For the Contract's `compute_budget`：
- **pilot_max_minutes** / **pilot_max_samples**：pilot 規模的硬上限，不是「先跑跑看」
- 完整規模的預估（compute hours、API 成本、wall clock、storage）供 `scale_up_rule` 判斷要不要升級
- 超出合理範圍就在 Contract 的 `abort_rule` 寫清楚什麼情況要喊停，不是跑到天荒地老

## Step 5: Config Stub Generation

Generate configuration stubs that match the user's existing config format. Read existing configs first to match file format、key naming、目錄結構、既有的 tracking 整合。`baseline.config_ref` 和 `treatment.config_ref` 指向這兩份實際存在的設定檔，不是描述。

## Step 6: 凍結 Experiment Contract

把上面的決定寫成一份符合 `records/experiments/schemas/experiment-contract.schema.json` 的 JSON，存到 `records/experiments/definitions/<experiment_id>.json`，`status` 設 `draft`。

跑 `experiment-lint`（見該技能）驗證：必填欄位齊全、baseline 跟 treatment 的設定檔之間沒有 `controlled_variables` 以外的未宣告差異。lint 沒過不要 lock。

過了以後把 `status` 改成 `locked`，跑 `uv run --project .agents/tools/experiment-records python -m experiment_records contract-hash <definition> --write` 算出 `contract_hash` 並寫回——不要手算，雜湊用 RFC 8785 正規化，手算會對不上。lock 之後這份檔案不得再改——要改 `top_k`／model／dataset／budget／metric 實作／evaluation set 等任何一項，開新的 `experiment_id` 或新的 treatment condition，不得原地覆寫。

## Step 7: Analysis Plan

Before running, define how results will be analyzed，寫進 Contract 或隨 run 記錄：

- 對應 primary/secondary metric（見 `records/experiments/schemas/metric-definition.schema.json`，metric 的實際算法要版本化）
- Statistical significance test if applicable（paired t-test, bootstrap CI）
- decision_rule 已經在 Contract 裡凍結，分析階段不得為了讓結果好看而改判準
- 每個 run 的紀錄格式見 `run-envelope.schema.json`；跑錯的 run 標 `invalid` 並填 `invalid_reason`，不得刪除

## Verification Checkpoints

Before finalizing the experiment plan:
- [ ] Each ablation changes exactly one variable（或已明確聲明為多因素設計）
- [ ] Baseline is clearly defined and will be run with same setup
- [ ] `compute_budget`／`abort_rule`／`scale_up_rule` 都填了
- [ ] Config stubs match existing project format，`config_ref` 指向真實存在的檔案
- [ ] `experiment-lint` 通過，`contract_hash` 已計算
- [ ] Seeds are fixed for reproducibility

## Output

1. **Experiment Contract**（寫入 `records/experiments/definitions/<experiment_id>.json`，lock 後帶 hash）
2. **Experiment matrix table** — all runs with their configurations（給人看的摘要，權威版本是 Contract 本身）
3. **Resource estimate** — compute hours、API 成本、storage
4. **下一步**：告訴使用者要跑 `experiment-lint` 驗證 Contract，通過才開始執行 run
