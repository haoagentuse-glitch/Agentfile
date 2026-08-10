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

## 核心規則：不准跳級，不自動解析規則文字

`compute_gate.py` 只認 `L0→L1→L2→L3→L4→L5` 這個順序，跳一級就直接擋（exit code 2），沒有例外，也沒有「這次先跳過 pilot 直接跑 full」這種選項——昂貴的實驗不是預設權利，這是規則 12 講的。

Contract 裡的 `scale_up_rule`／`abort_rule` 是自然語言，例如「pilot recall 提升 > 3pp 才跑 full」。**你要自己把這句話翻成參數**：

```
「pilot recall 提升 > 3pp 才跑 full」
  → --scaleup-metric recall_at_k --scaleup-comparator ">" --scaleup-threshold 0.03
     --scaleup-field absolute_diff --comparison <pilot 跟 baseline 的 compare-runs 輸出>
```

翻得對不對是你的責任，`compute_gate.py` 不會幫你判斷「3pp 這個門檻合不合理」，它只會告訴你「翻好的這組參數，比對實際數字，有沒有過」。

## 用法

```bash
python3 profiles/experimental/skills/compute-gate/compute_gate.py \
  records/experiments/gates/<experiment_id>.json \
  --request-level L2 \
  --scaleup-metric recall_at_k --scaleup-comparator ">" --scaleup-threshold 0.03 \
  --comparison records/experiments/comparisons/<xxx>.json \
  --output records/experiments/gates/<experiment_id>.json
```

- `--abort-*` 系列：任何等級都可以帶，abort_rule 觸發直接判 `aborted`，這條實驗路線視為終止，不是「這次沒過，改天再試」。
- `--contract` + `--pilot-run`：只在 `--request-level L3` 時生效，檢查 pilot 實際耗時有沒有超過 Contract 的 `compute_budget.pilot_max_minutes`。
- 都不帶（只有 `--request-level`）：只做序列檢查，沒有 abort／scale-up／預算條件——適合 L0（理論檢查本來就不需要跑數字）或你已經在別處確認過條件、只是要記一筆升級。

## 讀結果

- `PASSED`：`current_level` 更新，可以往下一級走。
- `FAILED`：這次帶的證據不夠，`current_level` 不動，可以補證據後重新申請同一級——不是死路。
- `ABORTED`：abort_rule 觸發，這條路線終止。不要繞過去改參數重跑，去看 abort_rule 本身設得合不合理，或這個方向本來就該停。

`gate-state.json` 是 append-only 的稽核軌跡，跟 run 一樣不覆寫舊紀錄——`history` 裡每一筆都留著，包括失敗跟中止的申請，不是只記成功的那次。
