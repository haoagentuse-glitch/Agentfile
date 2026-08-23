---
name: implement
description: "依 spec 或一組 ticket 實作一段工作。"
disable-model-invocation: true
metadata:
  source: mattpocock/skills@84fdeffd12f2ee307994d1eb6feb48173b6e0502（改寫成中文，非逐字保留）
  license: MIT
---

實作使用者在 spec 或 ticket 裡描述的那段工作。

能用 /tdd 的地方就用，並且只在事先講好的 seam 上測。

型別檢查要常跑，單一測試檔要常跑，完整測試套件在最後跑一次。

做完之後用 /code-review 審查這段工作。

把工作 commit 到目前的分支。
