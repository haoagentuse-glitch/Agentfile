---
name: claim-audit
description: >
  Use before presenting an experimental conclusion, writing up results, or
  whenever a claim cites a run/comparison as evidence. Mechanically verifies
  the claim traces to a real, non-confounded comparison with matching numbers,
  then the agent judges whether the claim's scope matches what the evidence
  actually covers. Triggers on "does the data support this", "audit this
  claim", "can we say X improves Y".
metadata:
  source: 概念參考 ARA（arXiv 2604.24658）的 claim → experiment → evidence 綁定鏈，
    schema 與判準是本包自己設計，不是 vendor（ARA 本身也沒有可 vendor 的實作，
    見 ADR 0006）。
---

# Claim Audit

完成 `Experiment Contract → Run → compare-runs → claim-audit` 這條鏈的最後一步。分兩段，職責不同，不要混在一起做：

1. **機械段**（`claim_audit.py`，確定性）：claim 引用的 run／comparison 存不存在、comparison 是不是 confounded、claim 講的方向跟幅度跟實際數字對不對得上。這段不用你判斷，跑腳本就有答案，同一個 claim 跑兩次要給一樣的結果。
2. **語意段**（你，agent）：機械段過了以後，claim 的**適用範圍**有沒有超出證據實際涵蓋的東西？這是唯一需要你判斷的部分——「這個結論有沒有超出證據範圍」沒辦法寫成規則機械判定，才交給你，不是偷懶少做。

## 用法

```bash
python3 profiles/experimental/skills/claim-audit/claim_audit.py records/experiments/claims/<claim-id>.json \
  --output records/experiments/audits/<claim-id>.json
```

固定慣例把結果存到 `records/experiments/audits/<claim-id>.json`——experiment-viewer 只會自動掃描這個路徑。exit code 0：機械段過了，`scope_verdict` 是 `pending`，換你判斷。exit code 1：機械段沒過，`final_verdict` 已經是 `unauditable` 或 `unsupported`，不用也不該再判斷 scope——連數字都不對的 claim，範圍判斷沒有意義。

## 獨立審核包

語意段要獨立，就不能一邊寫主張一邊審自己寫的東西。先組出審核包，換一個 context 或換一個人來看：

```bash
uv run --project .agents/tools/experiment-records python -m experiment_records review-package . <claim-id> --output records/experiments/artifacts/<claim-id>-review.json
```

包裡有凍結的研究問題、候選主張、比較結果的三個可比較性判定、把 `locator` 實際取出來的證據摘錄，以及全部 run 的摘要（含失敗與作廢的）。包裡**沒有** `producer`——審核者不該知道這個主張是哪個 agent、用哪版 prompt 寫的，知道了就會被它帶著走。

審核者只看這個包。包裡找不到答案的問題，正確做法是判 `unauditable`，不是回頭翻專案。

Contract 的 `review_policy.required_reviewer_kind` 決定誰有資格審。它跟 Contract 一起凍結，`experiment_records validate` 會比對稽核紀錄的 `reviewer_kind` 是否滿足——看到結果之後才放寬審核標準，等於沒有審核。

## 機械段過了之後，怎麼判斷 scope

讀 claim 的 `scope` 欄位（宣稱的適用範圍）跟它實際引用的 comparison 涵蓋了什麼（哪個 `dataset`、哪個 `model`、哪個條件——回頭看 comparison-result 跟它引用的 Experiment Contract），四選一：

| 判定 | 什麼情況 |
|---|---|
| `fully_supported` | claim 宣稱的範圍跟證據實際涵蓋的範圍一致，沒有多講 |
| `partially_supported` | 核心數字陳述正確，但宣稱的範圍比證據涵蓋的稍寬，不過還算合理延伸（例如同一個 `model` 家族的其他版本） |
| `overreaching` | 把單一 `dataset`／單一 `model`／單一條件下的結果講成「一般都適用」「大部分情況」這類無保留的通用結論，證據完全沒涵蓋那個範圍 |
| `unsupported` | scope 本身沒問題，但機械段已經判定數字或方向對不上（理論上不會走到這裡才發現，機械段會先擋） |

判斷完把 `scope_reasoning` 寫清楚「證據實際涵蓋什麼」跟「claim 宣稱涵蓋什麼」之間的落差，`final_verdict` 抄 `scope_verdict` 的值，存回同一份 audit result 檔案（或用 `--output` 產生的檔案，讀出來改這兩欄再存回去）。

`scope_verdict` 還是 `pending` 的時候不得寫 `final_verdict`——「還沒判」不是一種結論。

## 其他要填的軸線

scope 不是唯一要判的東西。以下幾軸分開記，因為它們會分歧：一個 claim 可以數字全對、卻沒有回答原本的研究問題。

| 欄位 | 判什麼 | 不填會怎樣 |
|---|---|---|
| `entailment.verdict` | 證據是不是真的推得出這句話，而不只是跟它相關 | 相關被當成因果 |
| `intended_question_fit.verdict` | 有沒有回答 `definition.question` 本來要問的東西 | 技術上正確但答非所問的結論通過 |
| `novelty.status` | 新穎性有沒有獨立的文獻查核 | 憑模型記憶宣告新穎 |
| `review_independence.independent` | 審核者是不是獨立於產出者 | 自寫自審後自動接受 |

`novelty.status` 標 `novel_confirmed` 必須附 `source_refs`；沒查過只能是 `unverified`。`review_independence.independent` 為 `false` 時，`final_verdict` 不得是 `fully_supported`。這兩條由 `experiment_records validate` 機械擋下，不靠自律。

## 不要做的事

不要因為 claim 的 `statement` 讀起來很有道理就放寬判準。不要幫 claim 補充它沒說的限定詞再判它過——claim 寫了什麼就審什麼，寫得不夠精確是 claim 的問題，不是你幫忙圓回來的地方。機械段沒過的東西不要嘗試用語意判斷救回來——`comparison_valid: false` 是硬限制（規則 10），沒有例外。
