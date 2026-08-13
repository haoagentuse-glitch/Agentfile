---
name: experiment-lint
description: >
  Use before locking an Experiment Contract or running an experiment.
  Runs the canonical deterministic experiment-record validator.
---

# Experiment Lint

本技能只負責觸發與解釋結果。
機械驗證與生命週期寫入都由同一個 CLI 提供。

```bash
uv run --project .agents/tools/experiment-records python -m experiment_records validate .
```

它檢查全部 experiment record、project-ref、Contract config diff 和生命週期事件。
任何 `錯誤` 都會回傳 exit code 1。
先修正錯誤，再 lock 或執行 run。

不要直接呼叫套件內部函式。
不要用 LLM 取代機械驗證。
