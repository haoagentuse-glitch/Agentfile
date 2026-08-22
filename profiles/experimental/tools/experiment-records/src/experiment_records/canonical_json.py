"""RFC 8785 JSON Canonicalization Scheme（JCS）。

雜湊要能跨機器對得起來，序列化形式就必須訂死。鍵序、非 ASCII 轉義、分隔符空白，
三者任一不同就算出不同的雜湊。這裡採用 RFC 8785 而不是自己挑一組 `json.dumps`
參數：自訂形式只在本專案內一致，跟別的專案算出來的雜湊仍然不可比。

規則只有三條：鍵以 UTF-16 code unit 排序、數字用 ECMAScript 的最短往返表示、
字串只轉義 JSON 規定的字元且不加任何空白。
"""

from __future__ import annotations

import json
import math
from typing import Any


def loads_strict(text: str) -> Any:
    """解析 I-JSON；重複鍵與非 finite 數字一律拒絕。"""

    def object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"JSON object 的 key 重複：{key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"JSON 不接受非 finite 數字：{value}")

    return json.loads(
        text,
        object_pairs_hook=object_from_pairs,
        parse_constant=reject_constant,
    )


def canonicalize(value: Any) -> bytes:
    """回傳 value 的 RFC 8785 正規形式，UTF-8 編碼。"""
    return _serialize(value).encode("utf-8")


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        # json.dumps 的轉義規則跟 JCS 一致：只轉義 " \ 與控制字元，其餘原樣輸出。
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int):
        # 超過 2^53 的整數在 IEEE 754 double 裡已經不精確，JCS 以 double 為準。
        return str(value) if abs(value) <= 2**53 else _number(float(value))
    if isinstance(value, float):
        return _number(value)
    if isinstance(value, list):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    if isinstance(value, dict):
        pairs = sorted(value.items(), key=lambda pair: pair[0].encode("utf-16-be"))
        return "{" + ",".join(
            f"{json.dumps(key, ensure_ascii=False)}:{_serialize(item)}" for key, item in pairs
        ) + "}"
    raise TypeError(f"JCS 不接受這種型別：{type(value).__name__}")


def _number(value: float) -> str:
    """ECMAScript 的 Number::toString。這是 JCS 對數字的唯一形式。"""
    if math.isnan(value) or math.isinf(value):
        raise ValueError("JCS 不接受 NaN 或 Infinity")
    if value == 0:
        return "0"
    if value < 0:
        return "-" + _number(-value)

    digits, exponent = _shortest_digits(value)
    length = len(digits)
    if length <= exponent <= 21:
        return digits + "0" * (exponent - length)
    if 0 < exponent <= 21:
        return digits[:exponent] + "." + digits[exponent:]
    if -6 < exponent <= 0:
        return "0." + "0" * (-exponent) + digits
    suffix = f"e{'+' if exponent - 1 >= 0 else '-'}{abs(exponent - 1)}"
    if length == 1:
        return digits + suffix
    return digits[0] + "." + digits[1:] + suffix


def _shortest_digits(value: float) -> tuple[str, int]:
    """把 value 拆成 (digits, exponent)，使 0.<digits> × 10**exponent == value。

    repr 給的就是最短往返表示，跟 ECMAScript 取的位數相同；這裡只是換一種擺法。
    """
    mantissa, _, exponent_text = repr(value).partition("e")
    exponent = int(exponent_text) if exponent_text else 0
    integer, _, fraction = mantissa.partition(".")
    digits = integer + fraction
    significant = digits.lstrip("0")
    leading_zeros = len(digits) - len(significant)
    return significant.rstrip("0") or "0", len(integer) + exponent - leading_zeros
