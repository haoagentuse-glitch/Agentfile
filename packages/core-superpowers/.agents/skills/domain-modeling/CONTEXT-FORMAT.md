# CONTEXT.md 格式

## 結構

```md
# {Context 名稱}

{一到兩句，說明這個 context 是什麼、為什麼存在。}

## 語言

**Order**：
{一到兩句的術語說明}
_避免_：Purchase、transaction

**Invoice**：
交付之後寄給顧客的付款請求。
_避免_：Bill、payment request

**Customer**：
下單的個人或組織。
_避免_：Client、buyer、account
```

## 規則

- **要有立場。** 同一個概念有多種說法時，挑最好的那個，其餘列進 `_避免_`。
- **定義寫緊。** 最多一到兩句。定義它**是什麼**，不是它做什麼。
- **只收這個專案 context 特有的術語。** 一般的程式概念（逾時、錯誤型別、工具模式）不屬於這裡，就算專案大量使用也一樣。加一個術語之前先問：這是這個 context 獨有的概念，還是通用的程式概念？只有前者該進來。
- **自然形成群組時用小標題分組。** 所有術語都屬於同一個連貫領域的話，平鋪的清單就夠了。

## 單一 context 與多 context 的 repo

**單一 context（多數 repo）：** repo 根目錄一份 `CONTEXT.md`。

**多個 context：** repo 根目錄的 `CONTEXT-MAP.md` 列出有哪些 context、各自放在哪、彼此怎麼關聯：

```md
# Context Map

## Contexts

- [Ordering](./src/ordering/CONTEXT.md) — 接收並追蹤顧客訂單
- [Billing](./src/billing/CONTEXT.md) — 產生發票與處理付款
- [Fulfillment](./src/fulfillment/CONTEXT.md) — 管理倉庫揀貨與出貨

## Relationships

- **Ordering → Fulfillment**：Ordering 發出 `OrderPlaced` 事件；Fulfillment 消費它開始揀貨
- **Fulfillment → Billing**：Fulfillment 發出 `ShipmentDispatched` 事件；Billing 消費它產生發票
- **Ordering ↔ Billing**：共用 `CustomerId` 與 `Money` 型別
```

技能自己推斷適用哪一種結構：

- 有 `CONTEXT-MAP.md` 就讀它找出各個 context
- 只有根目錄的 `CONTEXT.md` 就是單一 context
- 兩個都沒有，就在第一個術語定案時才建根目錄的 `CONTEXT.md`

有多個 context 時，推斷目前的主題屬於哪一個。判斷不出來就問。
