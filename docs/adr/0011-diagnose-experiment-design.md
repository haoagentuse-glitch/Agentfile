# diagnose-experiment：vendor phd-skills/debug，把 probe 泛化成 failure taxonomy

規則 6「結果不好時先診斷，不得直接 optimize」一直沒有對應 skill。讀了 `phd-skills/debug`（MIT，commit `8d642d3`）全文 125 行，結構成熟、可直接 vendor 大部分骨架，不用重寫。

## 保留的部分（骨架照抄）

`probe → hypothesis → smoke → controls → claim` 這條五步紀律整個保留，包括：

- 「先蒐證再猜」的核心主張（最貴的錯誤是憑合理性斷言原因、然後用掩蓋症狀的方式「修好」）
- hypothesis 一定要標成 hypothesis，不能跳到「原因是 X」
- smoke 是驗證假設最便宜的方式，一次只推翻一個假設
- controls 是 smoke 結果不明確時才需要的下一步，一次只換一個變因
- claim cause 一定要引用實際的探測輸出，證據不夠就講「還不知道」，不硬給答案——這條直接跟 `claim-audit` 的精神一致，這裡產生的 cause 陳述如果要變成正式的實驗結論，一樣要過 `claim-audit`
- 「What to avoid」與輸出格式（探測結果→假設→smoke 結果→原因或存疑→建議下一步）

## 改的部分：probe 跟 smoke 對照表泛化

上游整支 skill 是為 ML 訓練寫的：Step 1 的探測清單是 `nvidia-smi`／`dmesg`／checkpoint 目錄；Step 3 的 smoke 對照表是 OOM／data／model／optimizer／distributed 五種訓練特有的假設。這包的 experimental profile 涵蓋 RAG、agent 架構、ML/DL、模擬、檢索與排序、最佳化、演算法比較，不是只有 ML 訓練，照搬會讓其他六種領域的人覺得這個技能跟自己無關。

把 Step 1 改寫成一份**failure taxonomy**：依「執行狀態／資源狀態／輸入資料狀態／日誌與追蹤／狀態持久化／設定漂移／上下游依賴」七個類別分類，每類底下才依領域給具體探測方法——ML/DL 沿用上游的 GPU／checkpoint 例子，RAG／檢索另外給「直接查 index 繞過 LLM 層」「檢查 embedding 有沒有塌縮成同一個向量」這類例子，agent 架構給「單步 trace」「直接呼叫可疑的 tool 繞過整個迴圈」，模擬給「固定 seed 跑兩次比對」「跑 zero-step 檢查初始狀態」，最佳化／演算法比較給「用手算過的小案例驗證目標函數」。

Step 3 的 smoke 對照表同樣依領域各給幾組「假設 → 最便宜的驗證方法」，不是只有 ML 訓練那五種。Step 4 的 controls 常見軸也依領域各補幾個例子，不只是 mixed-precision／gradient checkpointing 這些訓練特有的東西。

## 沒改的部分

沒有另外寫確定性 script。這個技能本質上是調查方法論——選哪個假設、探測結果怎麼解讀、要不要繼續往下查，都是判斷，跟 `evidence-review`／`experiment-design` 同一類，不是 `experiment-lint`／`compare-runs`／`claim-audit`／`compute-gate` 那種有明確機械可判定規則的類型。勉強寫一支「自動診斷」腳本只會變成用規則模擬判斷，比不寫更危險。

沒有引入上游的 Stop hook 自動路由（`reason` 觸發）——跟先前所有 vendor 決策一致，這包不裝 hook。

## Consequences

- `diagnose-experiment` 是繼 `compare-runs`／`claim-audit` 之後第三個部分借用 phd-skills 內容的 skill，跟前兩者一樣：流程骨架借，內容依這包的實際領域範圍重寫。
- 探測方法的領域例子不是窮舉——目前只給每個領域 2-4 個代表性例子，不是完整診斷手冊。真的遇到例子沒覆蓋的情境，這個技能的價值在紀律本身（先探測、標記假設、smoke 驗證），不在例子多不多。
