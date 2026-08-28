---
name: api-contract
description: HTTP API 的契約驅動開發——先寫 OpenAPI 規格，models 與契約測試都由它生成。用於新增或修改 HTTP 端點，或討論 API 介面形狀的時候。
---

# API 契約

`openapi.yaml` 是 API 介面的唯一來源。models 與契約測試都由它生成，兩者皆不得手改。

## 迴圈

1. **寫或修改 `openapi.yaml`。** 這是設計步驟，其他東西一律不先動。
2. **生成 models。**
   ```bash
   uv run datamodel-codegen --input openapi.yaml --input-file-type openapi --output src/<pkg>/models.py --output-model-type pydantic_v2.BaseModel --target-python-version 3.12 --disable-timestamp
   ```
   `--disable-timestamp` 是**必要參數**，不是美化：少了它，生成器會把當下時間寫進檔案，每次重生成都不同，下面的漂移檢查永遠不可能通過。

   產出是建置產物。絕不手改——下一次重生成會無聲地把你的修改丟掉。
3. **跑契約測試。** 此時應該紅，因為還沒有任何實作。
4. **實作 handler**，對著生成的 models 寫，直到契約測試轉綠。
5. **交棒給 `tdd`** 處理行為。

## 契約測試

不需要跑伺服器——直接把規格綁到 ASGI 應用上：

```python
import schemathesis
from <pkg>.app import app

schema = schemathesis.openapi.from_path("openapi.yaml")
schema.app = app


@schema.parametrize()
def test_api_obeys_its_contract(case):
    case.call_and_validate()
```

測試案例由規格生成，不要手寫。

第一次跑通常會抓到框架會發出、但規格從未宣告的狀態碼——FastAPI 對無法解析的 body 回 `400`，手寫的規格幾乎必然漏掉。那是契約測試在做它該做的事。**改規格或改 handler，絕不放寬測試。**

## 兩層測試各自負責什麼

`schemathesis` 只檢查實作有沒有遵守規格：

- 回應符合宣告的 schema
- 沒有未宣告的狀態碼，沒有未宣告的 500
- 宣告的限制確實拒絕它說會拒絕的東西

**它不檢查行為是否正確。** 一個回傳格式完美、schema 合規、內容完全錯誤的端點，能通過所有契約測試——把使用者給的標題存下來的 handler，跟寫死 `"placeholder"` 的 handler，對契約測試而言完全無法區分。

業務行為與 regression 由手寫測試負責，走 `tdd` 的 red-green-refactor。該寫的案例就寫，這裡沒有禁止手寫測試的規則。契約測試縮小了手寫測試要涵蓋的面，不取代它。

## 漂移

生成的程式碼會漂移：有人手改了產物，或改了規格卻沒重新生成。在 CI 與本機都要守——重新生成，然後要求零差異：

```bash
uv run datamodel-codegen --input openapi.yaml --input-file-type openapi --output src/<pkg>/models.py --output-model-type pydantic_v2.BaseModel --target-python-version 3.12 --disable-timestamp && git diff --exit-code src/<pkg>/models.py
```

差異非空，代表提交的產物與規格不一致。修規格或重新生成——絕不靠改產物解決。

生成的檔案排除在專案的 lint 與 format 規範之外。它們是產物不是原始碼：格式是生成器的事，而一條只能靠手改產物才能滿足的規則，遲早會被手改產物滿足。

## 更動已發布的契約

破壞已發布端點屬於難逆決定，不在實作過程中順手做：先透過 `domain-modeling` 記一份 ADR，再改規格。
