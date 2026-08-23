---
name: domain-modeling
description: 建立並打磨專案的領域模型。用於使用者想釘死領域術語或通用語言、想記錄一個架構決策，或另一個技能需要維護領域模型的時候。
metadata:
  source: mattpocock/skills@84fdeffd12f2ee307994d1eb6feb48173b6e0502（改寫成中文，非逐字保留）
  license: MIT
---

# 領域建模

一邊設計，一邊主動建立並打磨專案的領域模型。這是**主動**的紀律——質疑用詞、造出邊界情境、詞彙與決策一成形就當場寫下來。（只是**讀** `CONTEXT.md` 查詞彙不算這個技能，那是任何技能都該有的一行習慣。這個技能用在你正在改動模型的時候，不是只在消費它的時候。）

## 檔案結構

多數 repo 只有單一 context：

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

根目錄有 `CONTEXT-MAP.md` 就代表這個 repo 有多個 context。那份地圖指出每個 context 放在哪：

```
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                          ← 跨系統的決策
├── src/
│   ├── ordering/
│   │   ├── CONTEXT.md
│   │   └── docs/adr/                 ← 這個 context 專屬的決策
│   └── billing/
│       ├── CONTEXT.md
│       └── docs/adr/
```

檔案要用到才建——有東西可寫的時候才建。沒有 `CONTEXT.md` 就在第一個術語定案時建；沒有 `docs/adr/` 就在需要第一份 ADR 時建。

## 進行中

### 拿詞彙表去質疑

使用者用的詞跟 `CONTEXT.md` 裡既有的說法衝突時，當場指出來。「你的詞彙表把 cancellation 定義成 X，但你現在講的像是 Y——到底是哪一個？」

### 把模糊的說法磨利

使用者用了含糊或一詞多義的詞，就提出一個精確的正式用詞。「你說 account——你指的是 Customer 還是 User？這是兩個不同的東西。」

### 用具體情境討論

在討論領域關係時，用具體情境去壓力測試。造出探測邊界的情境，逼使用者把概念之間的界線講清楚。

### 跟程式碼對照

使用者說明某件事怎麼運作時，去看程式碼同不同意。發現矛盾就攤出來：「你的程式碼取消的是整張 Order，但你剛說可以部分取消——哪個才對？」

### 當場更新 CONTEXT.md

一個術語定案，就當場更新 `CONTEXT.md`。不要累積起來一次寫——發生的當下就記下來。格式見 [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md)。

`CONTEXT.md` 裡不得有任何實作細節。不要把它當成 spec、草稿紙或實作決策的存放處。它只是一份詞彙表，別無其他。

### ADR 要省著提

三個條件同時成立，才提議建一份 ADR：

1. **難以回頭**——之後改主意的代價不小
2. **少了脈絡會覺得奇怪**——未來的讀者會想「他們當初為什麼這樣做？」
3. **是真的取捨出來的結果**——確實有其他選項，而你為了具體理由選了這一個

任何一條不成立就不要寫 ADR。格式見 [ADR-FORMAT.md](./ADR-FORMAT.md)。
