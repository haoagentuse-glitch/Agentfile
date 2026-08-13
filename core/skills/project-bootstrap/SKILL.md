---
name: project-bootstrap
description: 用這包建立新專案的骨架——套用技能與規範、建立 GitHub 儲存庫與分流標籤、備妥 Python 環境。用於專案啟動，或把既有專案納入這套規範。
---

# 專案骨架建立

## 前置確認

動手前先確認，缺一項就問，不要自己決定：

- 目標資料夾路徑
- 專案名稱
- 技術棧：Python（uv）／其他語言／先不定
- 目標資料夾若已有內容 → 列出來給使用者看過再動

## 步驟

### 1. 確認隨身包已套用

正常情況下這步已經完成——使用者是跑完 `apply.sh` 之後才被導到這裡的。確認目標資料夾有 `AGENTS.md` 與 `.agents/skills/` 即可，不要重跑。

真的還沒套用才跑，並先用 `--dry-run` 給使用者看過：

```bash
<隨身包路徑>/apply.sh <目標資料夾> --profile <software|experimental>
```

`--profile` 必須跟使用者要做的專案類型一致；不帶會退回 `software`。重跑只會更新沒被改過的投影檔，改過的一律不動並列進摘要。

### 2. GitHub 議題追蹤

`docs/agents/issue-tracker.md` 已由 `apply.sh` 交付並設定為 GitHub Issues。還缺的是實際的 repo 與標籤。

**建立遠端 repo 屬對外操作，執行前必須取得使用者明確同意**，並先問清楚公開或私有：

```bash
gh repo create <名稱> --private --source=<目標資料夾> --remote=origin
```

```bash
gh label create ready-for-agent --description "Ready for an agent to pick up" --color 0E8A16
```

`ready-for-agent` 是 `to-spec` 與 `to-tickets` 唯一使用的 triage 標籤，沒有它那兩個指令發 issue 會失敗。這兩個技能只存在於 `software` profile；其他 profile 仍建議建標籤，但不是必要的。

### 3. 跨 session 記憶

memsearch 負責跨 session 記憶，不需要每個專案設定——它把對話摘要成 memory Markdown，再建索引供之後檢索。未安裝的話：

```bash
uv tool install "memsearch[onnx]"
```

```bash
memsearch index docs/
```

索引不是必要步驟；沒有 memsearch，其餘流程照常運作。

### 4. Python 專案追加（技術棧選 Python 時）

```bash
cd <目標資料夾> && uv init --name <專案名> --python 3.12
```

```bash
uv add --dev pytest ruff
```

HTTP API 專案再加契約工具鏈：

```bash
uv add fastapi && uv add --dev schemathesis datamodel-code-generator
```

`software` profile 另外交付 `.claude/templates/python-pyproject.snippet.toml`，把裡面的設定段併進 `pyproject.toml`。其他 profile 沒有這份樣板，跳過即可。

版本一律釘選並提交鎖檔，禁 `latest`。

### 5. 語言無關骨架

只建立當下確實需要的目錄。**不要預建 `src/`、`lib/`、`utils/`、`tests/` 等空目錄** —— 違反 Structure Follows Need。
需要時再建，建立時放進真實檔案。

### 6. README

以 `.claude/templates/README.md` 為骨架寫 `README.md`，必填：

- 一句話說明專案做什麼
- 唯一入口（怎麼跑）
- 怎麼測、怎麼 lint

這三項的指令只寫在 README，別處引用。

### 7. 首次 commit

依 AGENTS.md，改動後自動 commit，不用等使用者指示。建議訊息：`chore: 專案骨架與開發規範`。

## 完成後

列出實際產生的檔案樹，並說明下一步：`software` profile 是 `/grill-me` 把需求問到收斂，`experimental` profile 是 `/evidence-review` 先看證據再選型。
