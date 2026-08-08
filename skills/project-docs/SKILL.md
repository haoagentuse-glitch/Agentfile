---
name: project-docs
description: 維護專案的長效文件——系統是什麼、為什麼長成這樣。用於系統的目的、範圍或結構改變後，文件已經對不上的時候。
---

# 專案文件

只放長效知識：系統**是什麼**，以及為什麼長成這樣。

## 職責邊界

本技能只擁有兩個檔案。其餘都有各自的擁有者，不要寫進去。

| 檔案 | 擁有者 |
|---|---|
| `docs/PROJECT.md` | 本技能 |
| `docs/architecture.md` | 本技能 |
| `CONTEXT.md`（詞彙表） | `domain-modeling` |
| `docs/adr/` | `domain-modeling` |
| `openapi.yaml` | `api-contract` |
| issue | `to-spec` / `to-tickets` |

## PROJECT.md

```
PROJECT.md = 目的、範圍、系統概觀、穩定背景
           ≠ feature spec
           ≠ 任務清單
           ≠ 變更紀錄
```

**絕不把 issue 裡的 feature spec 抄一份進 `docs/`。** issue 本身就是 spec。發現自己在複述某張票要求什麼，立刻停手——那段內容已經有擁有者了。

有長效的東西可寫才寫。只有一段話的 `PROJECT.md` 就是一份合格的 `PROJECT.md`。

## architecture.md

延後建立——直到光看目錄結構已經看不出系統怎麼組起來為止。寫的是有哪些部件、誰跟誰講話、以及新人不知道就會違反的限制。不是逐檔導覽。

## 依專案規模伸縮

小專案只要 `PROJECT.md`。等到得跟人解釋各部件怎麼接起來，才加 `architecture.md`。兩者都不預建。

## 什麼時候該跑

系統長相改變之後跑，不是每張票做完都跑。觸發條件：範圍變了、增減了元件、限制改了、或新人問了文件答不出來的問題。

## 動筆之前

讀 `writing-for-agents` 並照它做——這些檔案每個 session 都會被讀進去，長度是反覆付出的成本。

先確認有沒有東西已經回答了這個問題。`CONTEXT.md`、某份 ADR 或某張 issue 已經寫過的，用連結指過去，不要重述。

## 寫完之後

文件寫好且正確之後，刷新語意索引：

```bash
command -v memsearch >/dev/null && memsearch index docs/ || echo "語意索引未更新"
```

尾巴的 `|| echo` 是必要的：少了它，memsearch 未安裝時短路的離開碼是 1，會被當成任務失敗。

文件才是交付物，索引只是它的快取。memsearch 不存在或索引失敗時，**任務仍然算成功**——在回報末尾說一句「語意索引未更新」就停在那裡。不要重試，不要安裝任何東西，不要讓它把一份寫好的文件變成一次失敗。
