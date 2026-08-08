---
status: accepted
---

# 對話也需要語意檢索，但語意後端不屬於 agentkit

agentkit 的職責是把 Claude、Codex、不同 worktree 的 session 歷史正規化成同一份專案級的結構化歷史層，不是搜尋工具。它新增 `agentkit export --markdown <dir>`，只做 SQLite → Markdown 的可重建投影，讓任意 semantic backend 去索引；agentkit 本身不 import、不呼叫、不檢查任何後端。

投影預設落在 `<git-common-dir>/agentkit/export/`，不進版控、不放 `docs/`——它是快取，隨時可從 SQLite 重建。

## 取代了什麼

ADR 0001 主張「對話只需要字面搜尋，不進語意索引」。該主張作廢。

實測顯示字面搜尋的涵蓋範圍太窄：查「向量資料庫」「為什麼不用外掛」「自動存檔」在 169 則訊息上全部回傳 0 筆，儘管這三件事都被討論過——當時用的詞是「LanceDB」「vendor」「SessionEnd hook」。**必須記得原本的用詞才找得到，而想不起用詞正是最需要檢索的時候。**

ADR 0001 的核心決定（語意層只用 CLI、必須可替換）仍然有效，只有「對話不需要語意檢索」這一條被本 ADR 取代。

## 分工

```text
agentkit SQLite   結構化歷史的唯一來源
raw transcript    原始證據
LIKE search       精確字面搜尋
Markdown export   語意搜尋的投影
semantic backend  可替換，v1 用 memsearch
```

## 對話與文件必須分開索引

實測發現把兩者放進同一個 collection 會**倒轉權威順序**。一次 session 的投影是 69 個 chunk，`docs/` 只有 8 個；查「語意層必須可替換」時，ADR 0001（標題就是這句）掉到第 2 名，輸給一段引述它的閒聊。查「為什麼不裝 memsearch 外掛」時 ADR 掉到第 3 名。

AGENTS.md 明定 Current Docs / ADR 的權威高於 Conversation Memory。共用索引時，檢索層以純粹的數量壓過了這個順序——問「為什麼這樣決定」拿回的是當時的討論，不是決策紀錄。

因此：

```bash
memsearch index docs/                                    # 預設 collection
memsearch index .git/agentkit/export/ -c agentkit_sessions
```

查詢時預設只看文件；要翻對話才加 `-c agentkit_sessions`。這讓檢索順序與權威順序一致。

## Consequences

對話會進向量庫，體積與隱私都要納入考量——投影在家目錄底下的 git 目錄內，不會隨 push 外流。

索引成本不低：98 KB 的對話在 CPU 上跑約 53 秒。因此不掛任何自動觸發，要更新就手動重跑。

當前 session 要等 `SessionEnd` 才進資料庫，因此「剛剛說過的話」搜不到。v1 接受，不加 watcher 也不做即時 tailing。

語意檢索對「用詞接近」有效（查「LanceDB 為什麼不用」得分 1.0），對「換完全不同的說法」仍然不可靠（查「向量資料庫」得分 0.5，配到不相關段落）。0.5 附近是沒有好答案時的墊底分數，不是命中。字面搜尋與語意搜尋互補，都不是萬能。
