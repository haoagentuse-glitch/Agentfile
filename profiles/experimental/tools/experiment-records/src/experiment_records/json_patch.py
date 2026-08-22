"""對 JSON 文字做「只改一個頂層欄位」的最小改動，其餘位元組原樣保留。

`contract_hash`這類欄位是事後蓋印上去的。若用 `json.dumps(document)` 整份重新
序列化再寫回去，縮排、鍵序、跳脫風格都可能跟原檔不同——一行的欄位變更變成整檔
的 diff。這裡直接在原始文字上做外科手術式替換：只有目標欄位的值那段位元組會變。

只認頂層 object 的鍵。巢狀結構一律用 `json.JSONDecoder().raw_decode` 整段跳過，
不比對字串內容——某個巢狀字串裡剛好寫著跟目標欄位同名的文字，不該被誤當成那個欄位。
"""

from __future__ import annotations

import json

_WHITESPACE = " \t\n\r"


def _skip_ws(text: str, index: int) -> int:
    length = len(text)
    while index < length and text[index] in _WHITESPACE:
        index += 1
    return index


def patch_top_level_field(text: str, field: str, value: object) -> str:
    """回傳把頂層 `field` 的值換成 `value` 後的文字；其餘位元組不變。

    `field` 不存在時，跟在最後一個既有欄位之後新增一筆，縮排比照最後一個既有欄位。
    重複鍵時比照 JSON 讀取語意，只替換最後一次出現的那個。
    """
    decoder = json.JSONDecoder()
    length = len(text)
    index = _skip_ws(text, 0)
    if index >= length or text[index] != "{":
        raise ValueError("頂層必須是 JSON object")
    index += 1

    value_span: tuple[int, int] | None = None
    last_key_prefix = ""
    has_pair = False
    while True:
        pair_start = index
        index = _skip_ws(text, index)
        if index < length and text[index] == "}":
            break
        key_prefix = text[pair_start:index]
        key, index = decoder.raw_decode(text, index)
        index = _skip_ws(text, index)
        if index >= length or text[index] != ":":
            raise ValueError("JSON 語法錯誤：鍵之後預期冒號")
        index += 1
        index = _skip_ws(text, index)
        value_start = index
        _, index = decoder.raw_decode(text, index)
        if key == field:
            value_span = (value_start, index)
        last_key_prefix = key_prefix
        has_pair = True
        index = _skip_ws(text, index)
        if index < length and text[index] == ",":
            index += 1
            continue
        if index < length and text[index] == "}":
            break
        raise ValueError("JSON 語法錯誤：欄位之後預期逗號或物件結尾")

    encoded_value = json.dumps(value, ensure_ascii=False)
    if value_span is not None:
        start, end = value_span
        return text[:start] + encoded_value + text[end:]

    closing_brace = index
    if has_pair:
        insertion = "," + last_key_prefix + json.dumps(field) + ":" + encoded_value
    else:
        insertion = json.dumps(field) + ":" + encoded_value
    return text[:closing_brace] + insertion + text[closing_brace:]
