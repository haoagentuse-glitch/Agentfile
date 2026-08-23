# apply.sh 用投影雜湊判定可否更新，不再一律跳過既有檔

`apply.sh` 原本對已存在的檔案一律跳過。這對使用者改過的檔是對的，對從未被動過的投影檔是錯的，而兩者分不出來。實際後果：commit `468dfde` 同時新增 `project-bootstrap` 技能並修正 `core/.claude/commands/kickoff.md`，下游重跑只拿到新技能，`kickoff.md` 因為已存在被跳過，斷鏈的舊版留在目標專案裡，最後靠人工 diff 覆蓋。同時目標專案沒有任何來源紀錄，「這包是不是舊的」只能人工去比對。

決定：投影時把內容雜湊記進目標專案的 `.agentfile/manifest.tsv`，來源版本記進 `.agentfile/source.json`。重跑時比對三個雜湊——本次組裝出的來源、manifest 記錄、目標現況——只有「目標現況等於當初投影的內容」才更新，其餘一律不動並回報。

## 為什麼是 manifest，不是 git blob 比對

另一個做法是不存 manifest，用 `git hash-object` 在上游歷史裡找出「目標檔是不是某個舊版的原樣副本」。它對單檔投影可行，但 `AGENTS.md`、`.gitignore`、`settings.json` 在包內沒有單一 blob 對應——那是 core 與 profile 組裝出來的結果，要判定就得在每個歷史 commit 上重跑一次組裝邏輯。manifest 記的是投影當下的**結果**內容，複合檔與單檔用同一條規則處理，也不要求下游還留著上游 repo。

`source.json` 與 manifest 是同一次投影的兩種讀者：前者給 agent 讀（回答「我來自哪個 revision、哪個 profile」，也讓 `upstream-feedback` 的回報帶得出版本），後者只給 `apply.sh` 自己讀。兩份都不寫本機絕對路徑。

## 兩種 mode

| mode | 用於 | 語意 |
|---|---|---|
| `full` | 一般投影檔 | 雜湊涵蓋整個檔 |
| `prefix` | `AGENTS.md`、`.gitignore` | 雜湊只涵蓋前 N 位元組，其後屬下游 |

`prefix` 靠的是 `core/AGENTS.md` 開頭已經寫死的不變量：「專案特化章節只追加於末尾，不改寫上游條文」。manifest 記下受管前綴長度後，更新時換掉前綴、原封保留下游追加段。沒有這個模式，最重要的那份檔會永遠拿不到上游更新——追加專案特化章節是常態，不是例外。改動的若是前綴本身（下游改寫了上游條文），沒有任何機制能自動合併，判為衝突。

## 判定表

`src` 為本次組裝的來源，`rec` 為 manifest 記錄，`dst` 為目標現況（`prefix` 模式取前 `rec.bytes` 位元組）。

| 情況 | 動作 |
|---|---|
| 目標不存在 | 寫入並記錄 |
| 無 `rec`，`dst == src` | 只記錄，靜默納管（backfill） |
| 無 `rec`，`dst != src` | 不動，列為「不明來歷」 |
| `dst == rec`，`src != rec` | **更新** |
| `dst != rec`，`src == rec` | 不動，**靜默** |
| `dst != rec`，`dst == src` | 只記錄，**靜默**（下游已自行採納，兩邊一致） |
| `dst != rec`，`src != rec` | 不動，列為「衝突」，保留舊 `rec` |
| `rec` 有、來源已無 | 不動，列為「上游已移除」 |

三個容易做錯的地方：

- 「下游改了、上游沒動」必須靜默。那是特化章節的常態，每次重跑都喊一次就沒人看輸出了。
- 衝突時保留舊 `rec`，讓它持續回報到人工處理完為止，不要自我修復掉。
- 但「人工處理完」要認得出來。下游把上游那份原樣採納之後，`dst == src`，已經沒有東西要決定；此時只對齊 manifest、不再回報。少了這一格，採納過的檔會每次重跑都再喊一次，真正需要人看的那幾筆被雜訊蓋掉。
- backfill 不需要旗標。既有專案沒有 manifest，第一次重跑就把「內容等於當前來源」的檔自動登記，只有真的不一樣的檔要人工處理一次。

manifest 可以刪掉重建，刪了只會退回 backfill，不會壞掉——所以它符合「衍生產物永遠可刪除重建」。但它不是快取：重建後「下游改過這個檔」這件事會退化成「不明來歷」，要人工判一次。權威來源仍是雙方的檔案內容本身，manifest 只是省掉那次人工判斷。

## 為什麼預設更新，而不是加 `--update`

重跑 `apply.sh` 本身就是明確、可審查的一次性動作，manifest 已經證明該檔與投影當下逐位元相同，覆寫不會弄丟任何東西。多一個旗標只會重演這次的 bug：忘記帶就拿不到修正。`--dry-run` 保留為預覽，走完整判定但零寫入。

這修訂了 [ADR 0003](0003-apply-copies-not-symlinks-to-dotfiles.md) 的一條 Consequence（「只補新檔，不覆寫既有檔案」），不動它的核心主張——複製而非 symlink 回家目錄，仍然成立。

## Consequences

- 上游對既有檔案的修正會在重跑時傳到下游，不必人工 diff。
- 目標專案帶得出自己來自哪個 revision 與 profile。`upstream-feedback` 的回報因此帶得出版本（見 [ADR 0015](0015-upstream-feedback-via-issues.md)）。**尚未**接進 `run-envelope`——那要改 schema，屬難逆決定，等真的需要「這個 run 跑在哪版規範下」時再單獨判斷。
- 上游移除的檔只回報不刪除。刪除是難逆動作，而這類事件罕見，v1 印出可複製的 `rm` 指令讓人確認。真的變成反覆發生的麻煩再升格。
- `apply.sh` 從「只新增」變成「會覆寫」，風險等級提高，因此補上 `tests/test_apply.py` 逐格覆蓋判定表。這是這個 repo 根目錄第一次有 Python 專案設定，它只用來當測試入口，不是套件。
- 這包自己不適用：`apply.sh` 拒絕以自己為目標（見 ADR 0003），根目錄那四個組裝產物仍要手動同步，見 [ADR 0005](0005-core-profile-isolation.md)。
- 依賴 `sha256sum`（GNU coreutils）。`apply.sh` 既有的 `find -printf` 本來就綁 GNU，不新增可攜性負擔。
