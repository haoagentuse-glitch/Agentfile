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
- 專案是什麼、範圍與系統概觀：[docs/PROJECT.md](docs/PROJECT.md)
- 詞彙表：[CONTEXT.md](CONTEXT.md)
- 架構決策：[docs/adr/](docs/adr/)
- 要做什麼：GitHub Issues

> 這些檔案都是需要時才建立，不預先產生。

## 設定

<需要的環境變數。實際值放 `.env`（不進版控），範例放 `.env.example`。>
