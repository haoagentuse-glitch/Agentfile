---
name: upstream-feedback
description: 把在本專案發現的規範缺口回報給上游 agentfile。用於 AGENTS.md、skill 或 profile 與實際情境衝突，而問題不只發生在這個專案的時候。
---

# 回饋上游

規範由上游投影下來。下游只能往上送觀察、證據與建議，**不得在下游改寫上游條文**——改了也傳不回去，下次重跑 `apply.sh` 只會變成一筆衝突。

回報管道是上游 repo 的 GitHub Issue。不另建檔案格式、不另建同步工具。

當前 repo 若沒有 `.agentfile/source.json` 而有 `core/AGENTS.md`，代表你人就在上游——不要開 issue 給自己，直接跳到最後一節。

## 先判斷：該不該回報

滿足任一項才回報：

- 問題出在 `core`、共用 profile 或共用 skill。
- 現行規範與實際使用情境直接衝突。
- 必須靠本地變通才能合理繼續。
- 合理預期其他專案也會遇到。
- 無法判斷是本專案特例還是上游缺口。

**單一專案的領域需求不回報**，就地調整即可。不確定就當作最後一項，回報並在內文寫明不確定。

## 步驟

### 1. 取來源資訊

```bash
cat .agentfile/source.json
```

拿 `agentfile_repo`、`agentfile_revision`、`profile` 三項。

沒有這個檔，代表這個專案是舊版 `apply.sh` 套的——請使用者重跑 `apply.sh` 補上，不要自己猜版本。`agentfile_repo` 欄位不存在（上游沒設 remote）時問使用者要 repo slug，不要自己找。

### 2. 決定 fingerprint

格式固定：

```
<component>:<problem-class>
```

`component` 是出問題的 skill、profile 或規範檔名；`problem-class` 是問題類別，不是這次的細節。例如：

```
experiment-design:pilot-required-fields
compare-runs:baseline-assumption
writing-for-agents:architecture-misrouting
```

**先找既有的 fingerprint 重用**，找不到合理匹配才新建。同一類問題散在多個 fingerprint 底下，就聚合不起來。

### 3. 查有沒有人報過

```bash
gh issue list --repo <slug> --label agentfile-feedback --state all --search "<fingerprint>"
```

包含 `--state all`：已關閉的也要看。若命中的 issue 已關閉，而本次觀察來自**修正之後**的 revision，那是退化，在該 issue 留言並請使用者決定要不要重開。

### 4. 建立或追加

命中 → 追加一次觀察，不開新單：

```bash
gh issue comment <編號> --repo <slug> --body "<內文>"
```

未命中 → 開新單，標題是 `<fingerprint> — <一句話>`：

```bash
gh issue create --repo <slug> --label agentfile-feedback --title "<標題>" --body "<內文>"
```

### 5. 內文欄位

固定七項，缺一項就補齊再送：

```
agentfile revision：<source.json 的 agentfile_revision>
profile：<software / experimental>
component：<出問題的 skill 或規範檔>
觀察：<實際發生什麼，寫得出重現路徑就寫>
期待行為：<規範應該怎麼講>
目前變通：<這個專案暫時怎麼繞過>
為何可泛化：<為什麼這不只是本專案的問題>
```

**只寫觀察與證據，不寫規範草稿。** 要不要改、怎麼改是上游的決定。

## 上游端：處理收到的回報

在 agentfile repo 裡做，不是在下游做。

```bash
gh issue list --label agentfile-feedback
```

逐條判斷。同一個 fingerprint 在兩個以上不同專案重現，是值得正式評估的訊號，不是自動採納的理由。

- **採納**：先寫 ADR 說明為什麼這屬於跨專案不變量，再改 `core/` 或對應 profile，補上會抓到這個缺口的測試或檢查，最後關閉 issue 並在留言引用 commit。
- **不採納**：加 `wontfix` 關閉，並寫一行理由——屬專案特例、屬誤用、已過時，或修改成本高於收益。

**不得跳過 ADR 直接改 canonical。** issue 記的是觀察，ADR 記的是決定，兩者不能混成一份。

新增規範、skill 或工具的門檻仍以 `AGENTS.md` 為準：同類失敗反覆發生且有具體證據才升格。一則回報不構成理由。
