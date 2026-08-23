# 指標效度與 lock 前的可行性檢查

指標定義目前只表達「這個數字怎麼算」。它沒有位置表達「這個數字被驗證到什麼程度、能不能承載判定門檻」。Contract lock 前的檢查也全是結構檢查：schema 有效、兩個條件只差宣告變因、`derivation` 欄位齊全——這些都通過，設計仍然可能在算術上不可執行。

三則下游回饋指向同一組缺口：[#10](https://github.com/haoagentuse-glitch/Agentfile/issues/10)（指標擋不住三種量測錯誤）、[#11](https://github.com/haoagentuse-glitch/Agentfile/issues/11)（`environment` 沒有任何工具讀）、[#2](https://github.com/haoagentuse-glitch/Agentfile/issues/2)（lock 前沒有供給檢查）。

研究依據見 [指標效度與可行性檢查的最小模型](../research/measurement-validity.md)。AERA／APA／NCME 的 Standards 與 FDA 的 biomarker qualification 都把效度綁在「用途」上：工具本身沒有效度，有效度的是它在某個用途下的詮釋。JCGM 的 VIM 則指出定義細節不足會替不確定度設下地板——分母換了就是換了 measurand。

## 決定

### 指標定義新增選填的 `validity`

四個欄位，對應四個不同的問題：

- `intended_use`：這個指標被驗證到可以用在哪。
- `evidence_refs`：支持上面那句話的證據在哪，`project-ref` 格式。
- `limitations`：已知會讓它失真的情況。
- `threshold_eligible`：能不能拿來承載判定門檻。

整塊 `validity` 選填。缺它是合法狀態，代表這個指標還沒被驗證過——**強制填只會生出一堆為了通過檢查而寫的空話**。但沒有它就享受不到門檻資格。

`threshold_eligible: true` 時必須有 `intended_use` 與至少一個 `evidence_refs`。沒有證據就宣稱可承載門檻，正是這次要擋的事。

### 門檻只能掛在有資格的指標上

兩條機械規則：

- Contract 的 `primary_metric` 引用的指標必須 `validity.threshold_eligible` 為 true。
- `compute_cascade` 的 `promotion`／`abort` 規則引用的指標必須 `validity.threshold_eligible` 為 true。

`secondary_metrics` 不受限——次要指標本來就是觀察用的，不承載判定。

### Contract 新增選填的 `feasibility_checks`

每項檢查四個欄位缺一不可：`name`（在回答哪個疑慮）、`command`（怎麼重跑）、`evidence_ref`（當初看到什麼）、`passed`（結論）。

validator 只檢查已宣告的檢查完不完整、`evidence_ref` 解不解析得到。**它不從 `derivation` 的散文裡猜數字。** 猜錯比不檢查更糟：那會做出一個看起來有防護、實際上會誤判的閘門。

「資料抽樣型實驗 lock 前要實跑供給檢查」寫進 `experiment-design` 技能，不寫進 validator——validator 判斷不出一份 Contract 是不是抽樣型設計，硬猜就會變成上一句要避免的東西。

### `environment` 明說它不進判定

`compare_runs.py` 對 `environment` 的引用次數是 0。描述改成明講「給人看的摘要，不進可比較性判定」，並指出參與判定的環境事實要放進 `config_ref` 的設定快照。

下游已經實測過這條路：把偵測到的環境事實寫成設定快照的頂層鍵之後，CPU 容器與 GPU 環境的差異被既有的未宣告差異偵測抓到。

## 拒絕的方案

### 整包搬下游那九個欄位

拒絕。`comparability_breakers` 是 config 快照的職責，`label_error_rate` 與 `test_retest_delta` 是 `evidence_refs` 指向的內容而不是新格子，`mde_at_n` 與 `retires_when` 是 `intended_use` 與 `limitations` 的具體寫法。九個欄位裡真正跨領域的資訊只有四種，其餘是這一種寫法的實例。

### 讓 confound 偵測解析 `environment` 的自由文字

拒絕。自由文字沒有可逐鍵比對的結構，解析規則會退化成一堆脆弱的字串比對。config 快照已經承擔這個角色，而且實測有效。

### 建立第二套結構化 environment schema

拒絕。它跟 config 快照重疊，兩者都會被寫，然後開始互相矛盾。

### 讓 validator 判斷證據夠不夠強

拒絕。validator 只檢查證據存不存在、指得到不到。夠不夠強是 `evidence-review` 與獨立審核的事，那需要讀內容並下判斷。

## 後果

- 現有的指標定義不必遷移，`validity` 是選填。但要當 primary metric 或 gate 門檻的指標必須補上。
- 下游 frus-agentic-rag_v2 可以把九個本地欄位收斂成這四個，並刪掉對應的 `EXCEPTION:`。收斂會遺失欄位名稱層級的結構（例如 `label_error_rate` 變成 `evidence_refs` 指向的一份文件），這是刻意的取捨：上游只保證跨領域成立的那一層。
- `experiment-design` 多一個 lock 前步驟。它產出的是紀錄，不是新的閘門。
- 這四個欄位若在第二份、領域不同的 fixture 上套不進去，代表判斷錯誤，該退回下游特例——這是預先寫下的翻盤條件。
