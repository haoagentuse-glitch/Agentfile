---
name: diagnose-experiment
description: >
  用於實驗跑失敗、發散、指標怪怪的、卡住、崩潰或行為不如預期時——在動手修之前。
  它強制 probe → hypothesis → smoke → controls → claim 這個順序。涵蓋 RAG、
  agent 架構、機器學習與深度學習、模擬、檢索與排序、最佳化與演算法比較，
  不限於訓練。觸發語包括「為什麼會失敗」、「診斷這個 run」、「指標看起來不對」，
  以及 debug this run、diagnose。
metadata:
  source: fcakyon/phd-skills@8d642d3e114ee1d1e4d000f918d71e9bf0453dc2 的 debug skill
    （裁切改編後改寫成中文——probe→hypothesis→smoke→controls→claim 五步紀律、
    「先蒐證再猜」的核心主張、輸出格式整段保留；Step 1 的探測清單跟 Step 3/4
    的對照表原本只寫 ML 訓練，改寫成涵蓋 RAG／agent 架構／模擬／最佳化與演算法
    比較的失敗分類，見 ADR 0011）
  license: MIT
---

# 實驗診斷

最貴的錯誤是憑「聽起來合理」斷言原因，然後動手「修」一個掩蓋症狀而非解決根因的東西。這個技能強制 `探測 → 假設 → smoke 驗證 → 控制變因 → 下結論` 這五步紀律，順序不能跳。規則 6 講的就是這個：結果不好時先診斷，不得直接調參最佳化。

## 什麼時候用

使用者剛說了類似這些話：

- 「為什麼這個 run 失敗／發散／變慢／卡住／當掉」
- 「這個指標看起來很奇怪」「recall 突然掉到 0」「這個 run 沒有在動」
- 「debug 這個」「診斷一下」「查一下這個 run 怎麼回事」
- 貼了一段 log 問哪裡有問題

## Step 1：便宜的探測——依 failure taxonomy 分類，不要只查一種

先蒐證，不要一開始就猜。依這七個類別找便宜的探測方法，不是每次都要全查，挑跟症狀相關的：

| 類別 | 在查什麼 | ML/DL 例子（上游原有） | 其他領域例子 |
|---|---|---|---|
| 執行狀態 | 這個東西真的在跑嗎 | `ps aux \| grep train`，process 還在不在、是不是 zombie | agent 迴圈卡在哪一步；模擬 process 有沒有提早結束 |
| 資源狀態 | 資源夠不夠、有沒有卡住 | `nvidia-smi`，GPU 使用率是不是 0 | 向量資料庫記憶體用量；模擬用的 CPU/記憶體 |
| 輸入資料狀態 | 輸入是不是預期的樣子 | 資料集路徑存不存在、格式對不對 | index 的文件數量對不對；retrieval corpus 是不是空的或版本錯了 |
| 日誌與追蹤 | 別只信使用者的轉述 | 讀訓練 log 最後幾百行，找 exception、NaN、提早停止的訊息 | 讀 agent 完整 trace（不是摘要）；讀模擬的事件日誌 |
| 狀態持久化 | 上次成功停在哪 | checkpoint 目錄，最後一個檔案多大、什麼時候寫的 | agent session 狀態／模擬存檔點是否完整 |
| 設定漂移 | 實際用的設定跟以為的一樣嗎 | 對照這次 run 的實際 config 跟預期的差在哪（可以直接借 `experiment-lint` 的 confound 檢查邏輯） | 同左，任何領域都適用 |
| 上下游依賴 | 依賴的外部東西還活著嗎 | 分散式訓練的其他節點 | embedding API／retrieval 服務／模擬用的外部引擎是否可連得上、回應是否正常 |

`dmesg`／`journalctl`／磁碟用量這些系統層探測，ML/DL 訓練直接沿用上游原文；其他領域視情況套用同樣的「執行狀態／資源狀態」概念，不用照抄指令。

## Step 2：假設，明確標成假設

蒐證完，說出「可能是什麼」，明確框成假設：

> 「假設：這個 run 是因為 OOM 被殺的，因為 dmesg 顯示 3 分鐘前有 oom-kill，process 也不見了。還沒排除的替代假設：(a) NFS 寫入逾時、(b) 被其他 process 手動 kill。」

不要直接跳到「原因是 X」。假設就是標記你還不知道什麼。

## Step 3：smoke——用最便宜的方式驗證或推翻假設

一次只推翻一個假設，30 秒的 smoke 勝過 30 分鐘的「重跑然後祈禱」：

| 領域 | 假設 | smoke 驗證方法 |
|---|---|---|
| ML/DL（上游原有）| OOM | `batch_size=1` 跑 1 步，撐過就是 OOM 沒錯 |
| ML/DL | 資料問題 | 換成合成的記憶體內資料集重跑，能動就是資料路徑有問題 |
| ML/DL | 模型問題 | 單一 batch 只做 forward、`eval()` 模式，看 loss 跟輸出是否正常 |
| ML/DL | optimizer 問題 | `lr=0` 重跑，loss 還是爆就不是 optimizer 的問題 |
| ML/DL | 分散式問題 | 單 GPU 跑一次，能動就是 DDP／NCCL 的問題 |
| RAG／檢索排序 | retrieval 結果是空的／不相關 | 繞過 LLM 層，直接對 index 下已知該有結果的查詢 |
| RAG／檢索排序 | embedding 塌縮 | 對兩段明顯不同的文字算 embedding，cosine similarity 不該接近 1 |
| RAG／檢索排序 | reranker 是問題 | 關掉 reranker，比較原始檢索結果跟重排後的結果 |
| agent 架構 | 陷入無限迴圈 | `max_iterations=1`，檢視單步 trace |
| agent 架構 | 特定 tool 靜默失敗 | 繞過整個 agent，直接用同樣參數呼叫那個 tool |
| 模擬 | 非決定性／seed 沒固定 | 固定 seed 跑兩次，diff 輸出 |
| 模擬 | 初始狀態設錯 | 跑 zero-step／no-op，檢查初始狀態是否符合預期 |
| 最佳化／演算法比較 | 目標函數寫錯 | 拿手算過答案的小案例去跑目標函數，對答案 |
| 最佳化／演算法比較 | 實作跟參考不一致 | 跑一個玩具規模、答案已知的案例，逐位元比對 |

## Step 4：controls——smoke 結果不明確才需要

一次只換一個變因重跑 smoke，縮小範圍是哪個機制造成的。常見軸：ML/DL 沿用上游（單來源 vs 多來源資料、worker 數、混合精度開關、gradient checkpointing 開關、`torch.compile` 開關）；RAG 可以換 `top_k`、換 embedding model；agent 架構可以換 tool 集合、換 max_iterations；模擬可以換 timestep 大小；最佳化可以換初始化策略、換 learning rate schedule。

## Step 5：下結論——一定要引用探測輸出

蒐證、smoke、控制變因都做過才斷言原因，斷言要引用具體的探測輸出：

> 「根因：NFS 寫入逾時。證據：dmesg 在 14:23 顯示 `nfs server X not responding`（跟最後一次 checkpoint 寫入同一分鐘），`batch=1` 的 smoke 重現了逾時。建議：checkpoint 先寫本機 scratch 目錄，每個 epoch 結束再同步回 NFS。」

證據撐不起來就講「還不確定」，提出下一個該探測的方向，不要硬給答案。這裡下的 cause 陳述如果要變成正式的實驗結論寫進報告，過一次 `claim-audit`——診斷過程本身的證據鏈也適用「結論要能追到證據」這條規則。

## 不要做的事

「大概是 X，來試試 Y」——不行，先探測。用小改動重跑當診斷手段——先 smoke，再有意識地決定要不要重跑。只信使用者的敘述而不重讀實際的 log——使用者可能沒看仔細。找到第一個看起來合理的原因就停——如果證據跟它矛盾，不能因為它先被想到就採用。

## 輸出

簡短的診斷報告：(1) 探測結果、(2) 假設、(3) smoke 結果、(4) 原因或存疑、(5) 建議的下一步。每個斷言都要能指回支撐它的探測輸出。

## 讓診斷留下來

生命週期走到終態（`execution_failed`、`pilot_failed`、`confounded`、`inconclusive`……）時，只留一句 `reason`，過幾週回頭看就說不出當初排除過什麼。這種時候把診斷寫成 `records/experiments/diagnoses/<diagnosis-id>.json`：

- `deterministic_facts`：從紀錄讀出來的事實，每條都要 `source_ref`。說不出來源的就是推測，該放另一欄。
- `hypotheses`：你的推測，每個標一種失敗分類與把握程度。
- `excluded_classes`：已經排除的分類與排除依據。
- `cheapest_next_test.distinguishes`：這個測試能分開哪幾個 `hypotheses.id`。

兩欄分開的用處是：讀的人一眼分得出哪些是已知、哪些是猜的。混寫的話，猜測會隨著時間被當成事實。

`experiment_records validate` 會擋下幾件事：`distinguishes` 指到不存在的假設（「能分辨假設」不能只是一句宣稱）、`deterministic_facts` 的 ref 解析不到，以及在沒排除 `execution`／`data`／`metric`／`confound`／`insufficient_power` 之前就判 `hypothesis_refuted`——假說被推翻是正式結論，不是最後的兜底選項。
