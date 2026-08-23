# 指標效度與可行性檢查的最小模型

## 問題

`metric-definition.schema.json` 目前擋得住「名稱與實作脫節」。它擋不住三件事，而這三件事是下游 frus-agentic-rag_v2 前身作廢三輪數據的直接成因（[issue #10](https://github.com/haoagentuse-glitch/Agentfile/issues/10)）：

1. 標籤誤差率未知，卻拿這個指標設判定門檻。
2. 量測儀器的非確定性沒有量化。
3. 分母隨設定機械改變，兩個 run 仍放在同一張表比較。

兩個相關缺口：`run-envelope.environment` 是自由文字、沒有任何工具讀它（[#11](https://github.com/haoagentuse-glitch/Agentfile/issues/11)）；Contract lock 前的檢查全是結構檢查，凍結的抽樣規格在凍結的資料範圍上湊不湊得出來，沒有機制會問（[#2](https://github.com/haoagentuse-glitch/Agentfile/issues/2)）。

本文件找出跨領域仍成立的最小欄位集合，不照搬下游那九個欄位。

## 來源發現

### 效度屬於「詮釋與用途」，不屬於量測工具本身

- **VERIFIED — 來源直接結論。** 效度是「證據與理論支持特定詮釋、用於特定用途」的程度。測驗本身沒有效度可言；有效度的是分數在某個用途下的詮釋，而所需證據隨詮釋與用途改變。[AERA／APA／NCME, Standards for Educational and Psychological Testing, 2014, 第 1 章](https://www.testingstandards.net/uploads/7/6/6/4/76643089/standards_2014edition.pdf)
- **VERIFIED — 來源直接結論。** FDA 認可一個 biomarker 時，只在陳述的 context of use 之下認可它；context of use 決定所需證據的等級。[FDA, Context of Use](https://www.fda.gov/drugs/biomarker-qualification-program/context-use)、[Biomarker Qualification: Evidentiary Framework](https://www.fda.gov/media/119271/download)
- **UNVERIFIED — 本專案推論。** 因此指標定義要能表達「這個指標被驗證到什麼程度、用在哪個用途」，而不是只表達「它怎麼算」。最小組合是「用途」加「證據位置」——兩者缺一，「已驗證」這句話就沒有對象。

### 定義不夠細，會替不確定度設下一個誰也降不下去的地板

- **VERIFIED — 來源直接結論。** definitional uncertainty 是量測不確定度的一個成分，源自 measurand 定義的細節有限，它是任何量測所能達到的實務最小不確定度。[JCGM 200:2012（VIM3）2.27](https://jcgm.bipm.org/vim/en/2.27.html)
- **UNVERIFIED — 本專案推論。** 指標的分母就是 measurand 定義的一部分。分母隨設定機械改變，等於換了一個 measurand；此時同名的兩個數字放同一張表，差的是定義本身，不是處理效果。這不是估計偏差，是比較對象不存在。
- **UNVERIFIED — 本專案推論。** 「儀器非確定性」在這個模型裡不是新欄位，而是效度證據的一種：它屬於 `evidence_refs` 指向的內容，不屬於 schema 的必填格。schema 只負責逼人指出證據在哪，不負責規定證據長什麼樣。

### 可行性是獨立的研究問題，不是「先跑跑看」

- **VERIFIED — 來源直接結論。** feasibility 研究回答「這個研究做不做得起來」；pilot 是它的子集——所有 pilot 都是 feasibility 研究，但不是所有 feasibility 研究都是 pilot。[Eldridge et al., 2016, PLoS One](https://pmc.ncbi.nlm.nih.gov/articles/PMC5153862/)、[CONSORT 2010 extension to randomised pilot and feasibility trials](https://pubmed.ncbi.nlm.nih.gov/27777223/)
- **UNVERIFIED — 本專案推論。** 對本包來說，「凍結的抽樣規格在凍結的資料範圍上湊不湊得出來」是算術上界問題，不需要完整 pilot：跑一道具名命令實際量一次供給就能回答。要求的是那道命令與它的輸出留下紀錄，不是要求一份 pilot 研究。
- **UNVERIFIED — 本專案推論。** 檢查結果必須以「命令 + 證據位置 + 通過與否」的形式留存。只寫「已確認可行」等於沒有紀錄——它重跑不出來，也無法在 lock 之後被反駁。

## 最小資料模型建議

### 指標定義的 `validity`

```yaml
validity:
  intended_use: "在 nq-open-eval-v3 上比較檢索設定的召回差異"   # 這個指標被驗證到可以用在哪
  evidence_refs:                                              # 支持上面那句話的證據在哪
    - "docs/evidence/label-audit.md"
  limitations:                                                # 已知會讓它失真的情況
    - "標籤由單一標註者產生，誤差率未量化"
  threshold_eligible: false                                   # 能不能拿來設判定門檻
```

- **UNVERIFIED — 本專案推論。** 四個欄位對應四個不同的問題：用在哪、憑什麼、什麼時候會壞、能不能承載門檻。少任何一個都會讓另外三個失去意義。
- **UNVERIFIED — 本專案推論。** `threshold_eligible: true` 必須有 `intended_use` 與至少一個 `evidence_refs`。沒有證據就宣稱可承載門檻，正是要擋的那件事。
- **UNVERIFIED — 本專案推論。** 「未知」是合法狀態。`threshold_eligible: false` 加上一句 `limitations` 是誠實的紀錄；缺 `validity` 整塊也合法，代表這個指標還沒被驗證過——但它就不能當 primary metric，也不能當 Compute Gate 門檻。

### Contract 的 `feasibility_checks`

```yaml
feasibility_checks:
  - name: "gold 每卷供給足以支撐 stratified-500-per-kind"
    command: "frus gold-shape --by volume --kind topic"
    evidence_ref: "docs/evidence/gold-supply.md"
    passed: true
```

- **UNVERIFIED — 本專案推論。** 四個欄位缺一不可：沒有 `command` 就重跑不出來，沒有 `evidence_ref` 就查不到當初看到什麼，沒有 `passed` 就不知道結論，沒有 `name` 就不知道它在回答哪個疑慮。
- **UNVERIFIED — 本專案推論。** validator 只檢查「已宣告的檢查」是否完整、`evidence_ref` 解不解析得到。它不從 `derivation` 的散文裡猜數字——猜錯會比不檢查更糟，因為那會製造一個看起來有防護、實際上會誤判的閘門。

### `environment` 的定位

- **VERIFIED — 下游實測。** `compare_runs.py` 對 `environment` 的引用次數是 0。把環境事實寫進去，等於做出一個沒有工具讀的欄位。
- **UNVERIFIED — 本專案推論。** 正確的位置是 run 設定快照：參與可比較性判定的 OS、硬體、runtime 與 tracing 事實放進 `config_ref` 指向的設定，未宣告的差異就會被既有的 confound 偵測抓到。`environment` 保留為給人看的摘要，但描述要明講它不進判定——否則它看起來像防護。
- **REFUTED — 不採用。** 讓 confound 偵測去解析 `environment` 的自由文字。自由文字沒有可逐鍵比對的結構，解析規則會變成一堆脆弱的字串比對，而下游已經實測過「放進 config 快照」這條路可行。

## 失敗條件

以下任一條成立時，這個模型就沒有達成目的：

1. 指標宣稱 `threshold_eligible: true`，卻沒有任何 `evidence_refs`。
2. Contract 的 primary metric 引用一個 `threshold_eligible` 不為 true 的指標。
3. Compute Gate 的門檻引用一個 `threshold_eligible` 不為 true 的指標。
4. `evidence_refs` 或 `feasibility_checks[].evidence_ref` 指到不存在的檔案。
5. validator 開始從散文猜數字。
6. 這四個欄位在第二份、領域不同的 fixture 上套不進去——那代表它們是下游特例，不該升格成上游契約。

## 明確不採用項目

1. 不整包搬下游那九個欄位。`comparability_breakers` 是 config 快照的職責（見 `environment` 那節），`label_error_rate` 與 `test_retest_delta` 是 `evidence_refs` 指向的內容而不是新格子，`mde_at_n` 與 `retires_when` 是 `intended_use` 與 `limitations` 的具體寫法。
2. 不建立第二套結構化 environment schema。config 快照已經承擔這個角色。
3. 不要求每個指標都有 `validity`。強制填會生出一堆為了通過檢查而寫的空話。
4. 不讓 validator 判斷「這個證據夠不夠強」。它只檢查證據存不存在、指得到不到；夠不夠強是 `evidence-review` 與獨立審核的事。
