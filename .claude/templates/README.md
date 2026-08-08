# <專案名>

<一句話：這個專案做什麼。>

## 跑法

唯一入口：

```bash
<單一命令>
```

## 開發

```bash
uv sync                  # 安裝依賴
uv run pytest            # 測試
uv run ruff check .      # lint
uv run ruff format .     # 格式化
```

> 這些指令只寫在這裡（SSoT）。其他文件要提到就連結過來，不要複製。

## 文件

- 開發規範：[AGENTS.md](AGENTS.md)
- 規格：[docs/SPEC.md](docs/SPEC.md)
- 任務計畫：[docs/PLAN.md](docs/PLAN.md)
- 架構決策：[docs/DECISIONS.md](docs/DECISIONS.md)

## 設定

<需要的環境變數。實際值放 `.env`（不進版控），範例放 `.env.example`。>
