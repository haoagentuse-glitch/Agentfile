# experiment-records

驗證 `records/experiments/` 內的 JSON record。

檢查項目：

- 八份 canonical JSON Schema Draft 2020-12。
- project-root-relative `project-ref`。
- 不可變生命週期 transition event。
- 生命週期事件的順序、連續性與合法轉移。
- comparison 與 audit gate 的 evidence record。
- `revise` 使用的新證據。

`lifecycle-state.schema.json` 是狀態、合法轉移與證據 gate 的唯一來源。
每次狀態轉移新增一個 `records/experiments/lifecycles/*.json`。
不得覆寫舊事件。
目前狀態由完整事件序列計算。
新增事件必須使用 `transition` 子命令。它用 exclusive create 拒絕覆寫。

## 專案內用法

```bash
uv run --project .agents/tools/experiment-records python -m experiment_records validate .
```

```bash
uv run --project .agents/tools/experiment-records python -m experiment_records transition . <EXPERIMENT_ID> <TO_STATE> --reason "<REASON>"
```

輸入也可以是 `records/experiments/` 或單一 JSON record。
驗證單一 lifecycle event 時，CLI 只能驗證該事件本身。
驗證整個 project 才能檢查完整事件序列。

## 本包開發

```bash
uv run pytest
```
