# 下游回饋走上游 repo 的 GitHub Issue，不自建回收管線

下游專案在實際使用中會發現規範缺口——某條規則與情境衝突、某個 skill 少了一步、某個 profile 的欄位要求套不到這個階段。這些觀察目前沒有回路：除非人工轉述，否則直接消失。上游也因此看不到「同一個問題在幾個專案重現過」。

評估過的另一個做法是在下游寫 `.agentfile/feedback.jsonl`，上游跑 `feedback sync` 回收，經 fingerprint 聚合後走 observed → candidate → recommend_accept → accepted → resolved 的生命週期。決定不做，改用上游 repo 的 GitHub Issue。

## 為什麼不自建管線

- `gh` 已經是這包的宣告依賴，`apply.sh` 本來就檢查它，software profile 的每日流程整個建在 issue 上。自建一套等於在已有 issue tracker 的專案裡再做一個 issue tracker。
- `AGENTS.md` 的職責邊界表已經指定「GitHub Issues 回答要做什麼」。回饋就是「上游該做什麼」的候選，放進 issue 不需要新規則，放進 JSONL 反而要新增一個擁有者。
- `sync` 必須知道有哪些下游 repo，那份清單只能是本機絕對路徑，不能進版控，也不能跨機器。issue 沒有這個問題：下游只要有 repo slug 就送得出去。
- 生命週期、去重、聚合、lineage 都有現成對應：label 是狀態，`--search` 是去重，同一 fingerprint 的留言串是聚合，關閉時引用的 commit 是 lineage。自訂六個狀態不會比這個更清楚。
- 尚無累積證據。到目前為止只有一則實際回饋。先用最便宜的通道跑一陣子，確認 fingerprint 慣例與升格判準夠不夠用，再決定要不要工具。這正是 `AGENTS.md` 對「新增工具」的門檻。

## 機制

`apply.sh` 寫進目標專案的 `.agentfile/source.json` 提供 `agentfile_repo`、`agentfile_revision`、`profile`（見 [ADR 0014](0014-apply-manifest-based-update.md)），下游 agent 不必自己記得來自哪一版。`core/skills/upstream-feedback/` 擁有判準、fingerprint 慣例、去重步驟與內文欄位，上游端的處理規則也在同一份，不拆兩處。

fingerprint 是 `<component>:<problem-class>`，當 issue 標題前綴用。它只是聚合用的標籤，不是永久唯一的 ID。

## 邊界

- 回饋只能上行。下游不得改寫上游條文，只能在 `AGENTS.md` 末尾追加專案特化章節；`core/AGENTS.md` 補了一行明講這件事。
- 採納必須先寫 ADR 再改 canonical。issue 記觀察，ADR 記決定，不合成一份。
- 一則回報不構成升格理由，門檻仍是「同類失敗反覆發生且有具體證據」。

## Consequences

- 新增面只有一個 skill、一行規範、一個 label，零程式碼、零新格式、零同步步驟。
- 需要網路與 `gh` 認證才送得出回饋。離線時觀察會留在對話裡而不是檔案裡，這是接受的代價——真的常態性離線再補本地暫存。
- 上游 repo 要有 `agentfile-feedback` label，一次性建立，不進腳本。
- 回饋量大到人工讀不完，或 fingerprint 慣例被證明不夠用時，再重新評估 JSONL 管線。屆時 issue 裡已經有真實資料可以拿來設計 schema，不必憑空猜。
