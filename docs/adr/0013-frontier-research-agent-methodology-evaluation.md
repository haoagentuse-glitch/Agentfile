# 前沿科研 agent 方法論評估：Aletheia／FirstResearch／FunSearch・AlphaEvolve

研究性 ADR，這輪只做研究跟記錄，不改任何 schema 或 skill 內容。使用者提供的研究方向裡有一句「目前仍維持原計畫：`compare-runs` 先完成」——這是舊資訊，`compare-runs`／`claim-audit`／`compute-gate`／`diagnose-experiment` 跟 `experiment-viewer` 現在都已經做完並跑通，不影響這輪的任務範圍，不糾結這點，按使用者這輪真正要的（純研究、不擴張實作）處理。

## 三個系統實際查證到的機制

### Aletheia（Google DeepMind，*Towards Autonomous Mathematics Research*，[arXiv:2602.10177](https://arxiv.org/html/2602.10177)）

Generator／Verifier／Reviser 三者分離，反覆互動直到 Verifier 核准或達到嘗試上限。關鍵不是「三個角色」這個表面分工，是 Verifier 的獨立性怎麼做到的：論文提到 *"decoupling a reasoning model's final output from its intermediate thinking tokens"*——Verifier 看到的是跟原本推理過程斷開的東西，不是接著 Generator 的思路繼續想下去。系統明確允許「承認解不出來」是合法輸出，論文原話：Aletheia *"often admits failure to solve a problem, a key feature that improved the efficiency of human-AI research collaborations"*——這不是缺陷，是刻意設計，因為研究者情願用原始解題能力換取更高的準確率。

### FirstResearch（*Auditable Question Formation for LLM Scientific Discovery Agents*，[arXiv:2607.05682](https://arxiv.org/abs/2607.05682)）

核心工件是 **Research Question Certificate**，把研究問題本身結構化成六個必填要素才算成立：assumptions（基本定義與隱含假設）、mechanism（機制模型）、tension／矛盾（跟現有知識的衝突點在哪）、falsifiable hypothesis（可證偽假說）、minimal decisive test（能區分假說真偽的最小關鍵實驗）、failure update rule（假說被否證後怎麼調整，預先定義）。論文的消融實驗顯示「certificate-centered core 是最強的組件」——不是「多加幾個欄位」的裝飾性結構，是這個方法論真正在起作用的部分。目的是讓問題「在下游執行前具有可檢查性」，直接對應這句話：LLM 產生的科學問題「可能聽起來可信，但未能暴露科學家應該檢查的機制、證偽者或假設」。

### FunSearch（[Nature, 2023](https://www.nature.com/articles/s41586-023-06924-6)）／AlphaEvolve（DeepMind，[arXiv:2506.13131](https://arxiv.org/abs/2506.13131)）

兩者共同的結構：權重凍結的 LLM 當變異算子提出候選程式，評分完全交給一個獨立、確定性的 evaluator 函式，不讓生成候選的模型自己判斷自己的候選好不好。「search-space lock」在 AlphaEvolve 的開源重現實作 [OpenEvolve](https://github.com/DataCraft-AI/openevolve) 裡有具體機制可查證：用 `# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END` 註解明確標出哪些程式碼區塊允許 LLM 修改，區塊外的東西一律保護、不能動。

## 對照這包現有機制：哪些已經有、哪些真的缺

### 已經有對應機制的（驗證原設計方向，不是新發現的 gap）

- **search-space lock**：`experiment-contract.schema.json` 的 `controlled_variables`（凍結、刻意保持一致的條件）+ `treatment.variable`（唯一允許變動的欄位）本質上就是 AlphaEvolve 的 EVOLVE-BLOCK 機制——凍結區 vs 可變區的宣告式劃分。`compare_runs.py` 的確定性比對（宣告變因之外任何欄位有差異即判 confounded）已經在機械執行這條規則。這輪查證後確認這個設計方向是對的，不需要改。
- **獨立且確定性的 evaluator**：`claim_audit.py`／`compare_runs.py`／`compute_gate.py` 的機械段本來就是跟產生 claim／跑實驗的那個 agent 分開的確定性腳本，跟 FunSearch／AlphaEvolve「evaluator 獨立於生成器」的精神一致。

### 明確缺少的（真正的 gap，記錄下來，這輪不動）

1. **evidence-review 只做 Support Search，沒有強制 Refutation Search。** 目前 `evidence-review` 的 Step 2（系統性搜尋）跟輸出格式（`Evidence` / `Selected approach` / `Why not alternatives` / `Major unknowns`）整個流程都是在找「支持某個候選的證據」，沒有一步要求主動找反例、已知 failure mode、方法失效條件、替代解釋、或「這個改善會不會其實是 confound 造成的」。這正是使用者這輪提的「雙向證據搜尋」原則要補的地方。
2. **claim-audit 的 `scope_verdict` 沒有結構性要求由獨立的推理路徑判斷。** 機械段（`claim_audit.py`）本來就獨立，但語意段「這個 agent 判斷 scope 有沒有超出證據範圍」目前只寫「你（agent）判斷」，沒有像 Aletheia 那樣明確要求這個判斷要用一條跟「產生這個 claim 陳述」時不同、沒看過那段推理過程的獨立 context 做——這其實正是這整個 session 裡使用者一直要求我做的「沒看過推理過程的視角」(fresh-eyes review) 那個實踐，只是還沒被寫進 `claim-audit` 的 SKILL.md 變成明文規則。
3. **沒有 Research Question Certificate 這個工件。** Research Gate 目前只要求「動手前先過 `evidence-review`」，但 `evidence-review` 的輸出格式裡没有強制展開 assumptions／mechanism／tension／falsifiable hypothesis 這幾項——candidate 選型的證據有蒐集，但「這個研究問題本身站不站得住腳」沒有被結構化檢查過。
4. **没有明確的 failure_update 概念。** `diagnose-experiment` 產生的輸出是「cause 陳述或存疑」，但沒有要求回答「原始 hypothesis 裡哪個 assumption 被這次結果削弱了、下一個該問的問題是什麼」——目前的失敗處理停在「這次為什麼失敗」，沒有連回「所以我們現在該怎麼調整研究方向」，容易變成使用者原本擔心的「只是不斷換方法重跑」。

## 最小修改建議（草案，這輪不套用，記下來供之後真的要做時參考）

- `evidence-review` 的輸出格式在 `Major unknowns` 之後加一個對稱的 **Refutation Search** 區塊，跟 `Evidence` 一樣要求列出來源，內容至少涵蓋：反例、已知 failure mode、方法失效條件、替代解釋、以及「這個改善是不是可能來自 confound」。
- `claim-audit` 的 SKILL.md 在「機械段過了之後，怎麼判斷 scope」這節加一句明文規則：這段語意判斷應該用一條沒看過「這個 claim 的 statement 是怎麼被寫出來」那段推理過程的獨立視角做——不是換一個人，是換一條沒被前面推理污染的 context。
- Research Question Certificate 這個概念，傾向**不建成獨立新檔案格式**，併入 `evidence-review` 輸出格式的既有結構（在 `Problem` 之後加 assumptions／mechanism／tension／falsifiable hypothesis 幾個欄位）——避免又新增一種檔案格式增加維護面。但這個「併入 vs 獨立」的決定留到真的要做的那一輪再拍板，這裡只是先記下傾向跟理由。
- `experiment-contract.schema.json` 可以考慮加兩個選填欄位（草案，不是這輪要套用的 diff）：
  - `falsifier`（string，選填）：什麼觀察結果會證明這個 hypothesis 是錯的——跟現有的 `decision_rule`（什麼算成功）、`abort_rule`（什麼時候中止）不同角度，`falsifier` 明確框在「否證」而不是「決策」或「停損」。
  - `failure_update_rule`（string，選填）：假設被否證後，原始 hypothesis 裡哪個 assumption 被削弱、下一個研究問題預期往哪個方向調整——跟 `diagnose-experiment` 的輸出銜接，把「這次為什麼失敗」跟「所以研究方向要怎麼調」接起來。

## Consequences

- 這輪沒有修改任何 schema、skill、或 `profiles/experimental/AGENTS.md`——上面四項 gap 跟三個 schema 欄位草案都只是記錄，不是已核准的變更。
- 不建 autonomous research loop、不引入新的大型框架——跟先前拒絕 Scholar Loop 的 Director/Reasoner/Governor 自動迴圈（見 [ADR 0006](0006-experimental-profile-upstream-evaluation.md)）同一個理由：這包的邊界是「機械判定的部分交給確定性腳本，語意判斷交給呼叫的 agent，但決定要不要繼續投入算力／要不要繼續往下做，永遠是人或呼叫的 agent 主動決定，不是系統自己接著跑」。
- 之後真的要做這幾項，依 Institutionalize Repeated Failures 的一貫做法：先看是不是已經有具體痛點（例如某次 evidence-review 真的漏掉了關鍵反例、或某次 claim-audit 因為沒有獨立視角判斷錯了 scope），不是因為「這是前沿方法論就該跟上」。
