# RAG 貫穿式骨架 fixture

一份可重放的完整研究紀錄，涵蓋 [ADR 0013](../../../docs/adr/0013-frontier-research-agent-methodology-evaluation.md) 定義的整條生命週期。用途是回答「這套契約長出來的紀錄實際上是什麼樣子」，不是示範怎麼做 RAG。

這裡沒有 `records/experiments/schemas/`。schema 只有 `profiles/experimental/records/experiments/schemas/` 一份，驗證時在暫存目錄組起來。

## 跑驗證

```bash
uv run --project profiles/experimental/tools/experiment-records pytest tests/test_rag_walkthrough_fixture.py
```

## 四條鏈

| experiment_id | 終態 | 這條鏈在示範什麼 |
|---|---|---|
| `rag-topk-recall` | `accepted` | 完整成功路徑：題目憑證 → 鎖定 → 試跑 → 算力閘門 → 完整執行 → 三次複現 → 比較 → 主張 → 稽核 → 獨立審核 |
| `rag-chunk-overlap` | `confounded` | 評分器在兩次執行之間換版，是未宣告的控制變因差異；提升無法歸因 |
| `rag-rerank-depth` | `execution_failed` | 評估集雜湊與 Contract 鎖定當下不符，`abort_rule` 觸發；不用部分資料硬跑 |
| `rag-query-rewrite` | `inconclusive` | 比較完全合法、數字也算得出來，但幅度低於門檻且沒有變異估計；證據不足是正式終態 |

## 幾個刻意做成這樣的地方

**失敗的複現保留在紀錄裡。** `topk-replication-4-oom` 因 GPU 記憶體耗盡標為 `invalid`。刪掉它會讓紀錄看起來剛好是三次成功，那是選擇性報告。

**通過機械檢查不代表回答了問題。** `topk-recall-claim` 的稽核結果 `mechanical_pass` 與 `scope_verdict` 都是通過，但 `intended_question_fit` 是 `partially_answers`——claim 沒有提 `definition.question` 後半段的延遲 guardrail。分軸才看得出這件事。

**新穎性以查過的來源為準。** 同一份稽核的 `novelty.status` 是 `prior_art_found`，附 `source_refs`。definition 的 `derivation.novelty_status` 當初標 `novel_claimed`，稽核把它降級——這正是稽核該做的事。

**不可引用有兩種原因。** `rag-chunk-overlap` 是 `confounded`（條件沒守住）。另一種是 `structurally_comparable=false`（沒有共同基準），本 fixture 沒有這條，因為它在 `compare_runs.py` 的端到端測試裡涵蓋了。

**證據不足沒有被改寫成弱版本的成功。** `query-rewrite-claim` 的 `status` 是 `inconclusive`，稽核 `final_verdict` 是 `unsupported`，`entailment.verdict` 是 `not_entailed`。數字正確但推不出因果。
