---
name: handoff
description: 把目前的對話壓成一份交接文件，讓另一個 agent 接手。使用者說 handoff、交接時使用。
argument-hint: "下一個 session 要做什麼？"
disable-model-invocation: true
metadata:
  source: mattpocock/skills@84fdeffd12f2ee307994d1eb6feb48173b6e0502（改寫成中文，非逐字保留）
  license: MIT
---

寫一份交接文件，把目前的對話摘要成新的 agent 接得下去的樣子。存到作業系統的暫存目錄，不要存進目前的工作區。

文件裡要有一節「建議技能」，列出接手的 agent 應該叫用哪些技能。

已經記在其他產物裡的內容不要重複一遍（spec、計畫、ADR、issue、commit、diff）。改成用路徑或網址指過去。

敏感資訊一律遮蔽，例如 API key、密碼、可識別個人身分的資料。

使用者有帶參數時，把它當成下一個 session 的重點描述，照著調整文件內容。
