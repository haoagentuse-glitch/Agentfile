# ADR 0013：研究型 Agent 的實驗生命週期與資料契約

- 狀態：已接受
- 日期：2026-08-11

## 背景

本文件決定既有 Experiment 標準資料模型如何承接研究型 Agent 從題目形成、反證搜尋、實驗定義、執行、比較、研究主張、稽核到失敗更新的完整流程，也劃分提示詞與確定性程式的責任邊界。

決策依據只採正式論文、官方技術報告、標準、官方文件與官方原始碼儲存庫。來源直接支持的事實與對本專案的推論分開記錄，避免把外部系統做法誤寫成已驗證的本地結論。

## 決定

### VERIFIED：外部證據共同支持的最小骨架

1. **研究題目必須形成可稽核產物，而不是停在提示詞對話。** FirstResearch 的研究問題憑證（Research Question Certificate）串起基本概念、假設、機制、張力、可證偽假說、最小決定性測試、預期觀察與失敗後更新規則；其消融結果支持這個核心，但樣本小且依賴 LLM 評審，不能外推成普遍科學能力。
2. **生成與驗證必須分離，而且驗證可以拒答。** Aletheia 將 Generator、Verifier、Reviser 分開，直到 Verifier 接受或達到嘗試上限；承認無解是提高可靠度的刻意設計。
3. **具有廉價客觀評估器的問題，應由程式執行與評估器主導選擇。** FunSearch 與 AlphaEvolve 都讓模型提出候選，再由獨立評估器依執行結果篩選；候選生成者不負責裁決自己的輸出。
4. **研究執行應分階段並逐級增加算力。** AlphaEvolve 採由便宜到昂貴的分級評估；AI Scientist-v2 將流程拆成可行性確認、超參數調整、研究議程與消融實驗，階段結束後再做複現與檢查點。
5. **新穎性與研究主張正確性不能依賴模型記憶。** AI co-scientist 顯示沒有外部搜尋時會高估新穎性；Aletheia 也顯示真實引用仍可能被錯誤歸因，因此有來源不等於來源支持該主張。
6. **完整來源追溯資訊應保存實體、活動、責任者與推導關係。** W3C PROV 與 MLflow Tracking 共同支持實驗系統至少要關聯執行紀錄、參數、程式版本、指標、資料集與產物。

### 對本專案的推論（INFERENCE）

目前標準資料模型的中後段骨架方向正確，不需要另建自主研究框架。主要缺口是題目推導的結構化紀錄，以及跨全程保存產生者、提示詞、模型、工具、輸入證據與輸出產物。

```text
題目接收
  → 研究問題憑證
  → 前置閘門（可行性／新穎性／反例／倫理）
  → 鎖定實驗定義
  → 試跑
  → 算力閘門
  → 完整執行／複現實驗／消融實驗
  → 確定性比較與混雜稽核
  → 候選研究主張
  → 主張證據稽核
  → 獨立審查
  → 接受／拒絕／修訂／證據不足
  → 依失敗結果更新研究問題憑證或實驗定義
```

最小變更原則是：**擴充 `definition` 與 `run`，不要立即新增大量頂層目錄或協調器。** Question Certificate 可先成為 experiment definition 的結構化 `derivation` 區塊；prompt provenance 可成為 run、claim、audit 共享的 `producer`／`generation` 區塊。只有多個實際 workflow 需要獨立查詢 question certificates 時，才升格成新 canonical entity。

## 決策依據

### 1. FirstResearch：先讓問題可稽核，再花錢執行

#### 一手來源

- Pipeline 先定義 primitives 與 assumptions，再建 mechanism model、找 tension、產生 candidate question，最後生成 Research Question Certificate。Certificate 不是 chain-of-thought，而是供人與 downstream agent 檢查的 structured scientific provenance。[論文 §2–3](https://arxiv.org/pdf/2607.05682)
- 每一階段輸出 Pydantic-validated JSON。Gate 包含 deterministic hard rules：必須有 falsifying observation、mechanism summary，且 derivation／falsifiability 分數達門檻；repair 後會重新跑 deterministic gate。[論文 §3.2](https://arxiv.org/pdf/2607.05682)
- Novelty-aware repair 會把寬泛問題推向 threshold、interaction、phase transition、failure regime 等 mechanism boundary。[論文 §3.2–3.3](https://arxiv.org/pdf/2607.05682)
- 初步 ablation 中移除 certificate 或 mechanism model 會大幅降低 judged score；但 benchmark 只有十個 LLM-agent topics、主要仍是 LLM judge、未執行真實實驗，作者明確限制結論範圍。[論文 §5–7](https://arxiv.org/pdf/2607.05682)
- 官方 artifact 保存 exact configs、prompts、saved outputs、package JSON、reports 與 no-API verification scripts，並把 stochastic regeneration 與 saved-artifact verification 分開。[FirstResearch 官方 repo](https://github.com/louiswang524/FirstResearch)

#### 對本專案的推論

- `definition` 應補 `derivation`：`primitives`、`assumptions`、`mechanism_model`、`tension`、`falsifier`、`minimal_decisive_test`、`expected_observations`、`failure_update`。
- `experiment-lint` 不應判斷「機制是否真的合理」，但可 deterministic 地檢查上述欄位存在、ID 可解析、falsifier 與 success criterion 不矛盾、failure update 指到具名 assumption。
- Prompt repair 只提出修訂版 certificate；是否通過 硬性閘門 仍由 code 決定。
- 不應直接照搬 FirstResearch 的 3/5 門檻或 LLM rubric。那些數字只在該 benchmark 被測過，對 RAG／軟體實驗沒有跨域有效性證據。

### 2. Aletheia：生成、驗證、修訂分離，並保留失敗

#### 一手來源

- Aletheia 由 Generator、Verifier、Reviser 組成，直到 verifier 接受或達到 attempt limit；它主要以自然語言運作並結合 search、browser 等工具。[Aletheia 論文 §2](https://arxiv.org/pdf/2602.10177)
- 作者觀察到，將 verification 與生成時的中間推理分離，有助於發現生成階段忽略的錯誤；agent 會承認「No solution found」，作者把較高 conditional accuracy 視為比強迫回答更有用。[Aletheia 論文 §2.2](https://arxiv.org/pdf/2602.10177)
- 工具使用沒有消除 citation 問題，只把問題從虛構文獻移到「真文獻、錯誤歸因」。[Aletheia 論文 §2.3](https://arxiv.org/pdf/2602.10177)
- 在 200 個可判定候選中，31.5% 技術上正確，但只有 6.5% 被人類判定為有意義地回答原問題；常見問題是對題目作了 vacuous interpretation。這是「測試通過不等於回答研究問題」的強反例。[Aletheia 論文 §3.3、§5](https://arxiv.org/pdf/2602.10177)
- 論文提出 Human-AI Interaction Card，並公開重要 raw prompts／outputs；官方 repo 也按研究結果保存互動產物。[Aletheia 論文 §6.2](https://arxiv.org/pdf/2602.10177)、[Aletheia 官方 repo](https://github.com/google-deepmind/superhuman/tree/main/aletheia)

#### 對本專案的推論

- Claim audit 必須分成至少三個軸：`technically_supported`、`answers_intended_question`、`novelty_status`。不能用單一 `valid: true` 混在一起。
- `inconclusive`／`no_result` 必須是合法終態，不得以空 metrics 或模糊摘要偽裝成功。
- 生成 claim 與審核 claim 的 prompt 必須使用分離 context，reviewer 只看到 frozen definition、run/comparison、evidence excerpt 與來源，不讀 claim writer 的隱藏推理。
- 人類或 agent 的重要介入應留下 interaction record；不必保存私密 chain-of-thought，但要保存輸入摘要、角色、動作、產物 ID、時間、工具與可公開的 prompt/output artifact。

### 3. FunSearch 與 AlphaEvolve：提示詞提出候選，評估器負責驗證

#### 一手來源

- FunSearch 的輸入是 `evaluate` function、初始 implementation 與可選 skeleton。LLM 產生候選；不執行、超時、超記憶體或 invalid output 的候選直接丟棄；通過者才存入 database。[FunSearch 論文 §FunSearch、§Evaluation](https://www.nature.com/articles/s41586-023-06924-6)
- FunSearch 特別指出最適問題具備：快速 evaluator、rich score、可隔離的待演化邏輯；proof 等缺少豐富客觀 score 的問題不在其目前甜蜜點。[FunSearch 論文 Discussion](https://www.nature.com/articles/s41586-023-06924-6)
- AlphaEvolve 讓人設定 problem definition、evaluation criteria、initial solution；LLM ensemble 產生／批評／演化候選，code execution 與 automatic evaluation grounding 搜尋。[AlphaEvolve 技術報告 §2](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf)
- AlphaEvolve 的 evaluation cascade 先用小規模、便宜測試排除錯誤或不 promising 的候選，再進昂貴測試；也支援多分數、平行評估與附帶 LLM feedback。[AlphaEvolve 技術報告 §2.4](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf)
- 在 FlashAttention 案例中，候選先以 randomized inputs 對 reference code 檢查 numerical correctness，最終仍由 human experts 確認所有輸入正確；這顯示搜尋 evaluator 與最終驗證不是同一層級。[AlphaEvolve 技術報告 §3.3](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf)

#### 對本專案的推論

- Prompt 可以提出 RAG chunking、retrieval、reranking 或 evaluator 的候選修改，但 run validity、metric 計算、resource budget 與 comparison validity 必須來自實跑 code。
- `gate` 要能表達 cascade：`preflight → pilot → main → replication → independent_review`，每級各有明確 input、threshold、budget、abort reason 與產出的 next-stage authorization。
- 只有在 evaluator 便宜、穩定且 score 足夠 informative 時，才值得做 evolutionary／tree search。現階段不要先建 population database、meta-prompt evolution 或大規模 agent coordinator。
- LLM feedback 可作 secondary diagnostic，不得和 primary metric 相加成不透明單一分數；若真的參與 selection，必須記錄 judge model、prompt、temperature、重跑一致性及 calibration。

### 4. AI co-scientist：反例搜尋與新穎性審查有用，但排序不代表事實

#### 一手來源

- Generation agent 會做文獻搜尋、模擬 debate、拆 testable assumptions；Reflection agent 分 initial review、full literature review、deep verification、observation review 與 simulation review。[AI co-scientist 論文 Supplementary Methods](https://arxiv.org/pdf/2502.18864)
- Deep verification 會把假設拆成 assumptions／sub-assumptions，獨立檢查哪些錯誤是 fundamental；simulation review 會尋找 potential failure scenarios。[AI co-scientist 論文 Supplementary Methods](https://arxiv.org/pdf/2502.18864)
- Ranking agent 以 Elo tournament 排候選，目的是分配科學家與 compute 注意力；作者稱它是 proxy，並非 correctness proof。[AI co-scientist 論文 Supplementary Methods](https://arxiv.org/pdf/2502.18864)
- Search ablation 中，無搜尋的 novelty rating 明顯較高，顯示模型會 hallucinate novelty；搜尋後 correctness confidence 與分類能力也改善。[AI co-scientist 論文 Supplementary Experiments](https://arxiv.org/pdf/2502.18864)

#### 對本專案的推論

- Preflight 應有一個「反方研究者」prompt：主動找既有反例、替代機制、隱藏變因、量測洩漏與會讓結果失效的 slice；輸出只能是 structured critique，不能直接阻擋執行。
- Novelty audit 必須帶查過的來源清單與逐主張 entailment；沒有搜尋只能標 `novelty_unverified`。
- 若未來候選很多，可用 LLM pairwise ranking 來安排 pilot 順序；排名要標為 heuristic，最終 promotion 仍由 budget、gate 與實跑 metrics 決定。
- FirstResearch 自己的 combination pilot 顯示 pre-certificate debate 可能稀釋 mechanism clarity，因此 debate 不應成為 MVP 必經流程；先做單一 counterexample critique，再量測其效益。[FirstResearch 論文 §5.3](https://arxiv.org/pdf/2607.05682)

### 5. AI Scientist-v2：採用分階段與複現實驗，不採無限制樹狀搜尋

#### 一手來源

- Experiment Progress Manager 有四階段：preliminary investigation、hyperparameter tuning、research agenda execution、ablation；每階段有停止條件、checkpoint，階段末做 replications 並保存 mean/std。[AI Scientist-v2 論文 §3.2.1](https://arxiv.org/pdf/2504.08066)
- 每個 experiment node 保存 plan、script、error trace、runtime、metrics、plots 與 feedback；執行失敗和視覺問題都保留成 buggy node，而非抹除。[AI Scientist-v2 論文 §3.2.2](https://arxiv.org/pdf/2504.08066)
- 作者也坦承只有三篇投稿中的一篇被 workshop 接受，且 novel high-impact hypothesis、實驗方法與 domain justification 仍是挑戰；tree search 帶來更高 compute 與 scalability 成本。[AI Scientist-v2 論文 §5](https://arxiv.org/pdf/2504.08066)

#### 對本專案的推論

- `run` 應具備 `stage`、`parent_run_id`、`attempt_kind`（pilot／debug／tune／main／ablation／replication）、`failure` 與 `resource_usage`，即可支援線性與簡單分支；暫時不需要通用 tree engine。
- Failed run 也是證據：保留 error class、exit status、stderr artifact、partial metrics、budget consumed 與 retry lineage，Viewer 不應只顯示 completed runs。
- replication 應是獨立 run，不應將多次執行平均後只留一個數字；comparison 可引用 aggregation artifact，但每個 constituent run 都可追溯。

## 採用的端到端實驗生命週期

以下是落地流程，不是來源原文；它把上述證據映射到本專案現有 canonical entities。

| 階段 | 權威輸入 | 主要產物 | deterministic gate | 可用 prompt 增強 |
|---|---|---|---|---|
| 0. 題目接收 | 使用者目標、範圍、限制 | topic brief | 必填、風險／資源邊界存在 | 澄清 primitives、找模糊詞 |
| 1. 可行性與反例研究 | topic、primary sources、現有系統 | question certificate draft | source URL/ID、falsifier、mechanism、failure update 齊全 | literature scout、counterexample hunter、mechanism builder |
| 2. 鎖定 Experiment Contract | certificate、可執行系統、metric definitions | locked definition | schema、ref integrity、單一 treatment diff、metric direction、decision/abort rule | design critic、confound suggester |
| 3. Walking skeleton / pilot | locked definition、最小 dataset | pilot run + artifacts | exit/status、hash、budget、最低樣本、sanity checks | failure diagnosis、log summarization |
| 4. Compute gate | pilot comparison、budget | gate decision | threshold 與 budget code；不可由 prose 覆寫 | evidence summary、風險說明 |
| 5. Main / ablation / replication | gate authorization、frozen config | runs | immutable config/data/code/prompt hashes；run schema | 候選實作／debug 建議 |
| 6. 比較與 confound audit | runs、definition、metric definitions | comparison | config diff、dataset/eval/model equality、metric math、sample alignment | 未宣告 confound 候選說明 |
| 7. Claim 形成 | valid comparisons、artifacts | claim draft | 每個 quantitative assertion 必須有 evidence ref | claim writer、alternative explanation |
| 8. Claim-evidence audit | frozen claim、comparison、source excerpts | audit | refs 可解析、數值重算、coverage、比較 validity | entailment reviewer、novelty reviewer |
| 9. 獨立 review | evidence-only package | review + disposition | reviewer identity/context separation、required checks | blinded reviewer；必要時第二模型／人類 |
| 10. 更新或收斂 | review、failures、original certificate | decision、next certificate | 合法 state transition、改判證據、lineage | failure-update proposer、next-test designer |

### 建議狀態機

```text
draft
  → preflight_failed | ready_to_lock
  → locked
  → pilot_running
  → pilot_failed | pilot_inconclusive | promoted
  → main_running
  → execution_failed | awaiting_comparison
  → confounded | invalid | awaiting_claim
  → claim_rejected | awaiting_review
  → accepted | rejected | inconclusive | revise
```

狀態轉移由 code 執行，prompt 只能提出 `proposed_transition` 與理由。任何 `revise` 都要指名被更新的 assumption／definition field 與新證據，避免負結果被敘事性地抹掉。

## 資料契約

### 1. `definition.derivation`

```json
{
  "derivation": {
    "primitives": [{"id": "retrieval_coverage", "definition": "..."}],
    "assumptions": [{"id": "a1", "statement": "...", "status": "unverified"}],
    "mechanism_model": {
      "summary": "top_k 增加提高 coverage，但可能引入 distractors 並消耗 context budget",
      "variables": ["top_k", "coverage", "distractor_rate", "latency_ms"]
    },
    "tension": "coverage 與 context noise / latency 的取捨",
    "falsifier": "在預先指定 slices 中 recall 無提升，或提升只來自 evaluator leakage",
    "minimal_decisive_test": "固定 corpus、queries、models，只掃 top_k 並重複三個 seeds",
    "expected_observations": ["..."],
    "failure_update": [{"when": "...", "update_assumption_id": "a1", "to": "refuted"}],
    "source_refs": ["source:..."],
    "counterexamples": ["..."],
    "novelty_status": "unverified"
  }
}
```

`primitives` 與 `assumptions` 要有 stable IDs，因為 claim audit 與 failure update 必須引用它們。不要保存模型私密 chain-of-thought；保存可公開、可審核的 derivation summary。

### 2. 共用 `producer`／`generation`

凡是 agent 生成或修改的 definition、claim、audit、review，至少記錄：

```json
{
  "producer": {
    "kind": "software_agent",
    "name": "research-question-builder",
    "model": "provider/model-version",
    "prompt_id": "research-question-builder@1",
    "prompt_hash": "sha256:...",
    "input_refs": ["source:...", "definition:..."],
    "tool_calls_artifact": "artifacts/...jsonl",
    "created_at": "..."
  }
}
```

這是 W3C PROV 的輕量映射，不必導入 RDF 或完整 PROV-O runtime。若模型 API 不提供精確版本，應忠實記錄實際可得識別符並標 `version_unresolved: true`，不能自行補值。

### 3. `run`

在既有 config、metrics、artifacts 外，補齊：

- `stage`：`pilot | tune | main | ablation | replication | diagnostic`
- `parent_run_id` 與 `attempt_kind`
- `code_commit`、`dirty_worktree`、`config_hash`、`dataset_id/hash`、`evaluation_set_id/hash`
- RAG 特有的 `corpus_snapshot_id/hash`、embedding/index build identity、retriever/reranker/generator/evaluator 完整模型識別
- `seed` 或明確的 `nondeterminism_sources`
- `command`（可具名重現的唯一入口）、起訖時間、環境摘要
- `resource_usage`、`budget_limit`、`abort_reason`
- `failure`：class、phase、exit code、可重試性、error artifact
- prompt-based component 的 prompt ID/hash、temperature、tool policy

### 4. `comparison`

Comparison 應把下列判斷拆開：

- `structurally_comparable`：schema／metric／sample key 是否一致。
- `controlled_variables_match`：除宣告 treatment 外，config、data、model、prompt、evaluator 是否相同。
- `confounded`：具名 differences 與嚴重度；不可由 LLM 直接決定。
- `statistical_summary`：每 metric 的 effect、uncertainty、replicate count、missingness。
- `decision_rule_result` 與 `abort_rule_result`：由 frozen definition 重算。
- `diagnostic_suggestions`：可由 LLM 提出，但與 validity 分欄。

### 5. `claim` 與 `audit`

Claim 最少拆成：

- `statement`：一次只說一個可驗證命題。
- `scope`：dataset、slice、metric、run set、時間與版本。
- `claim_type`：`descriptive | comparative | causal | novelty | mechanism | negative_result`。
- `evidence_refs`：指向 comparison、run、artifact 的具名位置，不只檔案。
- `status`：`candidate | supported | refuted | inconclusive | superseded`。

Audit 最少逐 claim 回答：

- evidence 是否存在且 hash 相符。
- comparison 是否 valid／confounded。
- 數值能否 deterministic 重算。
- evidence 是否真的 entail statement，而非只相關。
- claim scope 是否超出 evidence。
- 是否回答 original research question。
- novelty 是否有獨立 literature audit。
- reviewer 是否獨立於 producer。

## 提示詞與程式的責任邊界

| 能力 | 提示詞／Agent 可負責 | 確定性程式必須負責 | 禁止做法 |
|---|---|---|---|
| primitives／mechanism | 提候選定義、因果鏈、替代機制 | schema、ID uniqueness、ref integrity | 把流暢文字當已驗證機制 |
| 反例／反證搜尋 | 找 counterexample、boundary、adversarial slices | source capture、去重、查詢時間、artifact hash | 無搜尋卻宣告無反例 |
| novelty | 形成查詢、摘要 prior art、指出差異 | 保存查過的來源與查詢；未查即 `unverified` | 模型憑記憶宣告 novel |
| experiment design | 提 treatment、controls、slices、ablation | 鎖定 config、單一變因 diff、metric ref、budget | agent 執行後偷偷改 hypothesis |
| 實作／debug | 產生 code patch、解釋錯誤、建議下一步 | sandbox、test、timeout、exit code、commit/hash、artifact capture | 用「看起來可行」代替實跑 |
| metric | 建議 metric 與失效案例 | metric implementation/version、計算、direction、unit、missingness | LLM 手算主指標 |
| promotion gate | 摘要風險與原因 | threshold、abort、compute budget、state transition | LLM prose 覆寫 gate |
| comparison | 提醒可能 confound、解釋 anomaly | config/data/model/prompt diff、effect 計算、sample alignment | 讓 LLM 判 `comparison_valid` |
| claim | 寫 scoped candidate claim、替代解釋 | evidence refs、數值重算、coverage | 無 ref 的結論進 supported |
| entailment audit | 判斷語意支持程度並列不確定性 | 來源存在、hash、引用範圍、比較合法性 | 同一 context 自寫自審後自動接受 |
| failure diagnosis | 分類可能根因、提出 cheapest next test | error capture、retry limit、lineage、budget | 吞錯誤或偽裝 empty success |
| final disposition | 寫 reviewer narrative | 合法 status、required reviewers、manual approval policy | 用 Elo／單一 LLM 分數等同真實正確 |

## RAG 專題驗證案例

### 0. 不從「做一個 RAG」直接跳到 top-k 實驗

先把題目拆成 primitives：query distribution、corpus snapshot、chunking、embedding、index、retriever、top-k、reranker、context budget、generator、answer evaluator、retrieval evaluator。接著建 mechanism：例如提高 top-k 可能增加 relevant-document coverage，但也可能提高 distractor rate、壓縮有效 context、增加 latency，最終 answer quality 可能呈非單調曲線。

### 1. 反例與可行性研究

至少預先找以下會推翻「top-k 越高越好」的反例：

- corpus 有大量 duplicate／near-duplicate chunks。
- generator 的 context window 小，新增 evidence 排擠真正相關片段。
- reranker 已把前幾名做到飽和，額外召回只增加 noise。
- multi-hop query 需要多樣來源，單純 recall@k 高仍無法形成完整 evidence chain。
- evaluator 與 benchmark leakage 讓 answer score 看似提升。
- 某些 query slice（罕見實體、時間敏感、跨語言）方向相反。

Prompt 在這裡最有價值：產生替代機制與反例搜尋詞。Code 在這裡的責任是保存查詢、來源、時間與 certificate，不替模型保證反例已找完整。

### 2. 鎖定 definition

主問題應改寫成可拒絕的版本，例如：

> 在固定 corpus snapshot、embedding、reranker、generator 與 evaluation set 下，`top_k` 從 10 增至 30 是否讓預先指定 multi-hop slice 的 retrieval recall 絕對提升至少 0.05，且 answer citation precision 不下降超過 0.02、p95 latency 不超過 800 ms？

Definition 必須列：primary／guardrail metrics、slices、direction、decision rule、abort rule、replicate/seeds、controlled variables、minimal decisive test、failure update。這些欄位在第一個 treatment run 前鎖定。

### 3. 試跑與算力閘門

- 先驗證 pipeline 能重現 baseline、query IDs 對齊、artifact 完整、metric sanity checks 通過。
- Pilot 只跑小而代表性的 frozen subset；它的任務是偵測系統錯誤與 effect 上限，不是發表結論。
- 若 guardrail 已超標、comparison confounded、或提升遠小於 decision threshold 且 confidence 足夠，code gate 停止 full run；LLM 只能寫診斷摘要。

### 4. 完整執行、複現實驗與消融實驗

- 每次 run 保存 per-query records：retrieved IDs／scores、reranked order、context sent、answer、citations、latency、token/cost、metric components。
- 不只保留 aggregate recall／latency；否則 Viewer 無法 drill down 至失敗 slice，claim audit 也無法重算。
- 至少將 seed／provider nondeterminism 分成獨立 replication runs。
- Ablation 各自是一個 definition 或有明確 parent 的 run，不可把多個變因改在同一個 treatment 後聲稱機制成立。

### 5. 研究主張與稽核

合格 claim 應是：「在 dataset X 的 frozen v3、multi-hop slice、三個 replication 下，top-k 30 相對 10 的 recall 提升 Y，citation precision 變化 Z；不外推到其他 corpus。」

不合格 claim 包括：「RAG 變好了」、「top-k 30 證明比較好」、「這是 novel 方法」。前兩者 scope／metric 不足，後者需要獨立 literature novelty audit。

## 常見失敗模式與反例

| 失敗模式 | 外部反例／證據 | 本專案防線 |
|---|---|---|
| 問題聽起來像研究，但沒有 mechanism 或 falsifier | FirstResearch 指出 vague improvement claim 可被完整實作卻仍科學上失敗 | certificate hard gate |
| 技術上正確但回答錯題 | Aletheia 的 31.5% 技術正確只有 6.5% meaningfully correct | `answers_intended_question` 獨立 audit |
| hallucinated novelty | AI co-scientist 無搜尋時顯著高估 novelty | primary-source search artifact；未查即 unverified |
| citation 存在但不支持主張 | Aletheia 工具化後仍出現真文獻錯誤歸因 | source excerpt + entailment audit |
| 一次改多個變因卻聲稱因果 | 研究設計的一般 confound；LLM review 無法取代 config diff | controlled-variable deterministic diff |
| evaluator 可被投機／metric gaming | FunSearch／AlphaEvolve 的成功依賴 evaluator；它同時是適用邊界 | guardrail metrics、held-out slices、evaluator version/hash |
| 只留 aggregate，無法重算或診斷 | MLflow 與 AI Scientist-v2 都把 run outputs／artifacts 與 metrics 關聯 | per-record artifact + hash + schema |
| 單次 stochastic run 被當成穩定效果 | AI Scientist-v2 階段末使用 replications 與 mean/std | independent replication runs |
| 同一 agent 自寫、自審、自動接受 | Aletheia 顯示 verification 分離的價值；FirstResearch 也承認 LLM judge 不能替代專家 | context/model separation + evidence-only review |
| 失敗 run 被刪除，selection bias | AI Scientist-v2 保留 buggy node、error trace 與 feedback | failed run 成為一等公民 |
| 負結果沒有更新任何假設 | FirstResearch 把 failure update 綁到 certificate | failure update 指向 assumption ID |
| 搜尋分支無限制耗盡 compute | AI Scientist-v2 與 AlphaEvolve 都需要明確 stage/budget | cascade gate、attempt limit、abort rule |
| prompt 漂移導致 run 不可比較 | agent 系統依賴 prompts，但文字常被當隱藏設定 | prompt ID/hash 納入 config diff |
| 先看結果再改 primary metric／hypothesis | 自動寫作系統可產生合理事後敘事 | locked definition；任何修改新建 lineage |

## 實作清單

### P0：閉合生命週期契約與研究資料結構

1. **定義 Experiment Lifecycle 狀態與合法轉移（已實作）。** 每次轉移由 `experiment_records transition` 以 exclusive create 新增不可變 event。validator 由事件序列計算目前狀態。非法跳過 pilot／comparison／audit 會被拒絕；`inconclusive`、`confounded`、`failed` 是正式終態。
2. **擴充 experiment definition 的 `derivation`。** 驗收：certificate 能表示 primitives、assumptions、mechanism、tension、falsifier、minimal test、failure update、source refs；`experiment-lint` 有 deterministic hard checks。
3. **把 provenance 做成共享小型結構。** 驗收：agent 產出的 definition／claim／audit 可回溯 model、prompt ID/hash、input refs、tool artifact；run 可回溯 command、commit、config/data/eval/prompt hashes。
4. **補 run stage／lineage／failure／resource usage。** 驗收：pilot、main、replication、ablation、diagnostic 與 failed run 都能表示，不需新增通用 tree framework。
5. **強化 comparison contract。** 驗收：config、data、model、prompt、evaluator、sample identity 的 differences 都可列出；`comparison_valid` 與 `confounded` 只由 code 算；數值可重算。
6. **強化 claim→evidence audit。** 驗收：每個 claim 可逐項檢查 evidence existence、numeric recomputation、scope、intended-question fit、novelty status、review independence。
7. **建立完整 RAG 貫穿式骨架 fixture。** 驗收：topic/certificate → locked definition → pilot → gate → 3 replication runs → comparison → claim → audit → review 全鏈可由 fixtures 重放；至少含 confounded、failed、inconclusive 三條反例。

### P1：契約成立後加入提示詞與研究執行增強

8. **建立少量版本化 prompt roles，而非總控 mega-prompt。** 首批只做：`question-builder`、`counterexample-reviewer`、`experiment-design-critic`、`failure-diagnoser`、`claim-writer`、`evidence-reviewer`。驗收：每個 prompt 輸出 具型別 JSON、版本與 hash 進 provenance，且無權直接改 gate 狀態。
9. **實作 evidence-only independent review package。** 驗收：reviewer 看不到 writer 的隱藏推理，只收到 frozen contract、comparison、claim、evidence excerpts；可設定第二模型或 human-required policy。
10. **實作 compute cascade gate。** 驗收：preflight/pilot/main/replication 每級有預算、promotion、abort reason；重新執行同一輸入產生同一 gate decision。
11. **建立 failure taxonomy 與最便宜 next-test 建議。** 驗收：execution、data、metric、confound、insufficient-power、hypothesis-refuted、scope-mismatch 分類不混寫；agent 建議與 deterministic facts 分欄。
12. **Viewer 呈現研究 lineage。** 驗收：從 claim 可一路點回 comparison、runs、definition/certificate、sources/prompts；failed／inconclusive 不被隱藏。

### P2：各項前置條件成立後才評估後置能力

13. **候選 hypothesis ranking／pairwise tournament。** 只有當候選量已造成真實人工瓶頸才做；ranking 只安排 compute，不代表 truth。
14. **agentic tree search／evolutionary population。** 只有 evaluator 快、rich、穩定且單線 workflow 已證實會卡 local optimum 才做。
15. **meta-prompt evolution。** 先建立固定 prompt 的 regression dataset 與 prompt version audit；沒有這些，不應讓 prompt 自行演化。
16. **CSV／Parquet／DuckDB adapter。** 與研究流程語意正確性無直接關係，等 JSON canonical lifecycle 穩定後再做。

## 後果

- 本 ADR 是研究型 Agent 實驗生命週期的唯一決策來源；原始研究報告路徑不再保留。
- 提示詞負責形成候選、反例、診斷與研究主張；Schema、路徑、雜湊、比較、預算與狀態轉移由確定性程式負責。
- 實作順序固定為 P0 生命週期契約與研究資料結構閉合、P1 提示詞與研究執行增強、P2 各項前置條件成立後才評估的後置能力；沒有量測證據前不建立自主協調器。
- Viewer 維持唯讀，只呈現既有紀錄與診斷，不補寫或修復來源資料。

## 被拒絕的方案

- 不建立同時負責構想、寫程式、評審、升級算力與發布結果的單一研究型 Agent 提示詞。
- 不以 LLM 分數取代指標、Schema、雜湊、設定差異、預算或閘門。
- 不保存模型私密思維鏈；只保存公開、結構化且與決策相關的推導摘要與互動產物。
- 不把 FirstResearch 的 LLM 評分門檻直接當成本專案的正式閘門。
- 不先建通用多 Agent 協調器、樹狀資料庫或提示詞最佳化器。
- 不由 Viewer 補寫缺失資料；Viewer 維持唯讀，錯誤回到資料產生流程修正。

## 預登記的改判條件

目前決定是「先補研究問題憑證、來源追溯、閘門與稽核，再加入少量提示詞角色；不建立大型自主協調器」。以下證據會推翻或調整它：

1. 若現有 definition 已完整、穩定地保存 mechanism、falsifier、failure update 與 sources，則不新增重複 `derivation`，只補 lint／UI。
2. 若實際使用證明研究候選量很少，且反例審查提示詞沒有發現人工漏項，則提示詞增強降級為按需使用。
3. 若固定基準測試顯示 Agent 分支搜尋在相同算力預算下穩定優於線性生命週期，且評估器投機未增加，才提前實作樹狀搜尋。
4. 若同模型審核者與人類專家在高風險研究主張上的一致性不足，改為強制人工閘門，不允許僅由模型裁決。
5. 若提示詞不是系統行為的一部分，例如純確定性 RAG 流程，則只記錄實際存在的生成器與評估器提示詞，不強迫所有執行紀錄都有提示詞欄位。

## 一手來源索引

1. [FirstResearch: Auditable Question Formation for LLM Scientific Discovery Agents](https://arxiv.org/pdf/2607.05682)
2. [FirstResearch 官方 reproducibility artifact](https://github.com/louiswang524/FirstResearch)
3. [Towards Autonomous Mathematics Research（Aletheia）](https://arxiv.org/pdf/2602.10177)
4. [Aletheia 官方 prompts / outputs repo](https://github.com/google-deepmind/superhuman/tree/main/aletheia)
5. [Mathematical discoveries from program search with large language models（FunSearch, Nature）](https://www.nature.com/articles/s41586-023-06924-6)
6. [AlphaEvolve: A coding agent for scientific and algorithmic discovery](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf)
7. [AlphaEvolve 官方 verification results repo](https://github.com/google-deepmind/alphaevolve_results)
8. [Towards an AI co-scientist](https://arxiv.org/pdf/2502.18864)
9. [The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search](https://arxiv.org/pdf/2504.08066)
10. [W3C PROV-O](https://www.w3.org/TR/prov-o/)
11. [MLflow Tracking 官方文件](https://mlflow.org/docs/latest/ml/tracking/)
