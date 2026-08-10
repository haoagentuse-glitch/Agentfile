## Software Profile

追加於 `core/AGENTS.md` 之後，只講軟體工程專案的特化規則，不改寫上游條文。

### 專案結構與依賴（軟體特化）

- 每個 Python 專案獨立 `.venv`，禁全域依賴。
- 遵循 Python 3.12+ 最新 PEP。嚴格禁止（不可 EXCEPTION 豁免）：舊版專案配置、已廢棄型態寫法、SQL/Shell 的 f-string 拼接、過時併發模式。
- 版本釘選並提交鎖檔，禁以 latest 作為穩定策略。新增依賴須在 commit 訊息寫理由。

### 執行面（軟體特化）

規範入口恰有兩個：

- 營運／管線：`python -m <pkg> <subcommand>`，子命令集中註冊於一處，`--help` 即完整清單，README 只連到此。
- 測試：`pytest <node-id>`，不自建測試包裝。

```
✗ python -c "from proj.pipeline import run; run('ingest')"
✗ $env:MODE='dev'; python scripts/a.py
✗ cat > proj/task.py << 'EOF' ...
✓ python -m proj pipeline run --stage ingest
✓ pytest tests/test_ingest.py::test_schema
```

### 契約驅動

HTTP API 以 `openapi.yaml` 為唯一來源，models 與契約測試由其生成，皆為產物、禁手改。做法見 `api-contract` 技能。

- 契約測試只驗證實作符合 spec；業務行為與 regression 由手寫測試負責。契約全綠不代表行為正確。
- CI 必須重跑生成並確認零差異。有差異就修 spec 或重新生成，不得改產物。
