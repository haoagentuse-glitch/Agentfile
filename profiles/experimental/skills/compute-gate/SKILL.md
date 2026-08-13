---
name: compute-gate
description: >
  Use before scaling an experiment up to the next Compute Gate level (L0
  theory check through L5 full run), or when a pilot/ablation result comes in
  and you need to decide whether to proceed. Enforces sequential levels and
  checks abort/scale-up rules deterministically. Triggers on "can we scale
  this up", "run the full experiment", "should we abort this run".
---

# Compute Gate

`profiles/experimental/AGENTS.md` 定義的六級：L0 理論／靜態檢查 → L1 合成資料／確定性測試 → L2 小型資料集 → L3 小規模試跑 → L4 消融／敏感度分析 → L5 完整規模執行。這個技能負責機械判定「現在能不能升到下一級」，不負責決定「這個實驗到底有沒有前途」——那是 evidence-review／compare-runs／claim-audit 的事。

## 核心規則：不准跳級，門檻凍結在 Contract

`compute_gate.py` 只認 `L0→L1→L2→L3→L4→L5` 這個順序，跳一級就直接擋（exit code 2），沒有例外，也沒有「這次先跳過 pilot 直接跑 full」這種選項——昂貴的實驗不是預設權利，這是規則 12 講的。

Contract 裡的 `scale_up_rule`／`abort_rule` 是自然語言，例如「pilot recall 提升 > 3pp 才跑 full」。**你要自己把這句話翻成 `compute_cascade` 的欄位**，而且翻完之後跟 Contract 一起凍結：

```json
{
  "stage": "main", "level": "L4",
  "budget": { "max_wall_clock_seconds": 5400, "max_cost_usd": 18.0, "max_runs": 4 },
  "promotion": {
    "metric": "recall_at_10", "source": "comparison", "field": "absolute_diff",
    "comparator": ">=", "threshold": 0.03
  },
  "abort": {
    "metric": "latency_ms", "source": "run", "field": "value",
    "comparator": ">", "threshold": 400, "reason": "延遲超過 guardrail，這條路線終止"
  }
}
```

翻得對不對是你的責任，`compute_gate.py` 不判斷「0.03 這個門檻合不合理」。但翻譯只做一次，寫進 Contract，之後同一組紀錄重跑會得到同一個判定——門檻散在某次呼叫的命令列參數裡，就沒有這個性質。

`stage` 是研究階段（`preflight`／`pilot`／`main`／`replication`／`independent_review`），`level` 是花多少算力。兩個是不同的軸，所以分開記。

## 用法

```bash
python3 profiles/experimental/skills/compute-gate/compute_gate.py \
  records/experiments/gates/<experiment_id>.json \
  --contract records/experiments/definitions/<experiment_id>.json \
  --request-level L4 \
  --comparison records/experiments/comparisons/<xxx>.json \
  --run records/experiments/runs/<pilot-baseline>.json \
  --run records/experiments/runs/<pilot-treatment>.json \
  --output records/experiments/gates/<experiment_id>.json
```

`--run` 可以重複。預算檢查與 `source` 為 `run` 的規則都靠它；`source` 為 `comparison` 的規則要 `--comparison`。

判定順序固定：`sequence` → `abort` → `budget` → `promotion`，任一步失敗就停。中止檢查排在升級檢查前面，因為升級條件過了也不能蓋過中止條件。

取不到值時判 `failed`，不判通過——「不知道」不等於「符合」。

## 讀結果

- `PASSED`：`current_level` 更新，可以往下一級走。
- `FAILED`：這次帶的證據不夠，`current_level` 不動，可以補證據後重新申請同一級——不是死路。
- `ABORTED`：abort_rule 觸發，這條路線終止。不要繞過去改參數重跑，去看 abort_rule 本身設得合不合理，或這個方向本來就該停。

`gate-state.json` 是 append-only 的稽核軌跡，跟 run 一樣不覆寫舊紀錄——`history` 裡每一筆都留著，包括失敗跟中止的申請，不是只記成功的那次。

每一筆 `history` 帶 `checks`，逐項記下這次做了哪些檢查與各自的數字。決定要能回溯到數字，不能只留一句結論。要驗證判定可重現，用 `--decided-at` 固定時間戳重跑，比對兩次的 `history` 最後一筆。
