---
name: experiment-lint
description: >
  Use before locking an Experiment Contract or before running an experiment.
  Deterministically checks required fields and confounded baseline/treatment
  configs — not an LLM judgment call. Triggers after experiment-design drafts
  a Contract, or whenever the user asks "is this experiment identifiable" /
  "lint this experiment".
---

# Experiment Lint

這個技能不判斷任何事，只負責觸發跟解釋結果。真正的檢查是 `experiment_lint.py`——一支只用標準函式庫的 deterministic script，不是 prompt。能機械判定的規則（必填欄位齊不齊、baseline/treatment 的設定有沒有未宣告的差異）不交給 LLM 自由判斷，因為那樣同一份 Contract 不同次檢查可能給出不同結果，而這正是這個技能要防的事。

## 用法

```bash
python3 profiles/experimental/skills/experiment-lint/experiment_lint.py records/experiments/definitions/<experiment_id>.json
```

## 檢查什麼

1. **Schema 完整性**：對照 `records/experiments/schemas/experiment-contract.schema.json` 遞迴檢查必填欄位（`hypothesis`、`baseline`、`treatment`、`controlled_variables`、`primary_metric`、`decision_rule`、`compute_budget`、`abort_rule`……）跟 enum 限制（例如 `status` 只能是 `draft`／`locked`）。
2. **Confound 檢查**：讀 `baseline.config_ref` 跟 `treatment.config_ref` 指到的設定檔，逐 key 比對：
   - `controlled_variables` 裡宣告「應該一致」的欄位，實際卻不一致 → **ERROR**，擋住（exit code 1）。
   - 兩份設定有差異，但這個 key 既不是宣告的 `treatment.variable` 也不在 `controlled_variables` 裡 → **WARN**，提醒去 Contract 裡把這個差異講清楚，是變因還是控制變因。
   - 沒宣告 `seed` 相關的控制 → **WARN**。

## 讀結果

- 全部 PASS／WARN，沒有 ERROR → 可以 lock（`experiment-design` 的 Step 6）或開始跑。
- 有 ERROR → 先處理，不要手動略過。ERROR 通常代表 Contract 寫的跟實際設定檔對不上，這時候的實驗結果無法歸因，跑了也是浪費算力。
- config_ref 指的檔案還不存在會印 WARN 而非 ERROR——Contract 可以先 draft，等設定檔寫好再重跑一次 lint。

不把這支 script 包成 hook 自動觸發；`experiment-design` 的 Step 6 明講要手動跑這一步，維持「optional 工具不做成 mandatory lifecycle」——如果之後真的因為忘記跑而反覆出包，再依 Institutionalize Repeated Failures 升格。
