# experiment-records

驗證 `records/experiments/` 底下的實驗紀錄：完整 JSON Schema Draft 2020-12 驗證，
加上 Schema 以 `format: project-ref` 宣告之欄位的 project-root-relative 邊界檢查
（拒絕絕對路徑、`..` 跳脫、canonicalize 後的 symlink 跳脫）。

每次執行都會先驗證全部七份 canonical schemas；整包掃描時，未知的 record 類型會明確
報錯，不會被靜默略過。輸出同時列出命令、輸入、Schema 位置與 project commit。

## 用法

```bash
uv run python -m experiment_records validate <PROJECT_OR_RECORD>
```

`PROJECT_OR_RECORD` 可以是 project root、`records/experiments/` 目錄，或單一 record 的
JSON 檔案路徑。

## 測試

```bash
uv run pytest
```
