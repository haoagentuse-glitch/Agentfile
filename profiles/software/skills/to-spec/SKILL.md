---
name: to-spec
description: 把目前的對話變成一份 spec，發布到專案的 issue 追蹤系統——不做訪談，只把已經討論過的東西整合起來。
disable-model-invocation: true
metadata:
  source: mattpocock/skills@84fdeffd12f2ee307994d1eb6feb48173b6e0502（改寫成中文，非逐字保留）
  license: MIT
---

這個技能拿目前的對話脈絡與你對程式碼的理解，產出一份 spec。**不要**訪談使用者——把你已經知道的整合起來就好。

issue 追蹤系統設定在 `docs/agents/issue-tracker.md`，由這包投影過去。唯一在用的分流 label 是 `ready-for-agent`。

## 流程

1. 還沒探索過的話，先探索 repo，弄清楚程式碼現在的樣子。整份 spec 都用專案領域詞彙表的用詞，並遵守你動到的區域的 ADR。

2. 勾出你打算在哪些 seam 上測這個功能。既有的 seam 優先於新開的。用你能用的最高層 seam。真的需要新的 seam，就提在你能提的最高點。整個程式碼庫的 seam 越少越好——理想是一個。

跟使用者確認這些 seam 符不符合他們的預期。

3. 用下面的樣板寫 spec，然後發布到專案的 issue 追蹤系統。貼上 `ready-for-agent` 分流 label——不需要其他分流。

<spec-template>

## Problem Statement

使用者面對的問題，用使用者的視角寫。

## Solution

這個問題的解法，用使用者的視角寫。

## User Stories

一份**很長**的編號 user story 清單。每則 user story 的格式是：

1. 身為 <角色>，我想要 <功能>，這樣我就能 <好處>

<user-story-example>
1. 身為手機銀行的客戶，我想看到帳戶餘額，這樣我在花錢時能做出更有依據的判斷
</user-story-example>

這份清單要極度詳盡，涵蓋這個功能的每一個面向。

## Implementation Decisions

已經做出的實作決策清單。可以包含：

- 會建立或改動的模組
- 那些模組會被改到的介面
- 開發者給的技術澄清
- 架構決策
- schema 變更
- API 契約
- 具體的互動方式

**不要**寫具體的檔案路徑或程式碼片段。它們很快就會過期。

例外：某個原型產出的片段，比散文更精確地表達了一個決策（狀態機、reducer、schema、型別形狀），就把它內嵌在對應的決策裡，並簡短註明它來自原型。只留決策密度高的部分——不是一個能跑的示範，只要重點。

## Testing Decisions

已經做出的測試決策清單。要包含：

- 什麼算好測試的說明（只測外部行為，不測實作細節）
- 會測哪些模組
- 測試的前例（也就是程式碼庫裡類似的測試）

## Out of Scope

這份 spec 範圍之外的東西。

## Further Notes

關於這個功能的其他備註。

</spec-template>
