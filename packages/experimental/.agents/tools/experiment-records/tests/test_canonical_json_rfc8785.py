"""RFC 8785（JSON Canonicalization Scheme）官方測試向量。

只走 `contract-hash` 這個公開入口：餵一份 JSON，比對它印出的雜湊是否等於「RFC
給的正規形式」自己手算的 SHA-256。不匯入 `canonical_json.canonicalize`——那不是
文件裡承諾的公開入口（見 `project_snapshot.py` 檔頭：「只走公開入口：CLI 與
load_project」）。

來源：<https://www.rfc-editor.org/rfc/rfc8785.txt>。三組向量：
- Section 3.2.2 數字序列化 + Section 3.2.3 字串跳脫（官方例子把三者放在同一個物件裡）。
- Section 3.2.3 屬性排序：官方給的 7 個樣本鍵，依 UTF-16 code unit 排序。
- Appendix B：IEEE 754 binary64 位元樣式 -> ECMAScript Number::toString 的邊界值。
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from helpers import run_cli


def _digest(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _run_and_expect(tmp_path: Path, name: str, document: dict, canonical: str) -> None:
    path = tmp_path / name
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")

    result = run_cli("contract-hash", str(path))

    assert _digest(canonical) in result.stdout, result.stdout + result.stderr


# --- Section 3.2.2 input -> Section 3.2.3 canonical（數字 + 字串跳脫 + 字面量）---


def test_rfc8785_numbers_string_and_literals(tmp_path: Path) -> None:
    # 輸入字串逐字元語意：€ $ SI(U+000F) LF A ' B " \ \ " /
    string_chars = [
        chr(0x20AC), "$", chr(0x0F), chr(0x0A), "A", "'", "B", '"', "\\", "\\", '"', "/",
    ]
    document = {
        "numbers": [
            float("333333333.33333329"),
            float("1E30"),
            float("4.50"),
            float("2e-3"),
            float("0.000000000000000000000000001"),
        ],
        "string": "".join(string_chars),
        "literals": [None, True, False],
    }
    # JCS 只跳脫 " \ 與 < U+0020 的控制字元；其餘（含非 ASCII、正斜線）原樣輸出。
    expected_string_literal_body = "".join([
        chr(0x20AC), "$", "\\u000f", "\\n", "A", "'", "B", '\\"', "\\\\", "\\\\", '\\"', "/",
    ])
    canonical = (
        '{"literals":[null,true,false],'
        '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        '"string":"' + expected_string_literal_body + '"}'
    )
    _run_and_expect(tmp_path, "numbers-string.json", document, canonical)


# --- Section 3.2.3 property sorting：官方樣本鍵 -------------------------------


def test_rfc8785_property_order_uses_utf16_code_units(tmp_path: Path) -> None:
    keys_in_official_order = [
        "\r", "1", chr(0x80), chr(0xF6), chr(0x20AC), chr(0x1F600), chr(0xFB33),
    ]
    # 刻意用官方順序以外的順序建構，證明排序是工具做的，不是輸入順序照抄。
    document = {key: index for index, key in enumerate(reversed(keys_in_official_order))}
    canonical = "{" + ",".join(
        (f'"\\r":{document[key]}' if key == "\r" else f'"{key}":{document[key]}')
        for key in keys_in_official_order
    ) + "}"
    _run_and_expect(tmp_path, "property-order.json", document, canonical)


# --- Appendix B：IEEE 754 binary64 邊界值 -------------------------------------


# RFC 8785 Table 1 全部 finite rows。expected 逐字寫死、照抄 RFC 原文——
# 不由實作算出來，否則測試只是把實作的答案問實作一遍。
_APPENDIX_B_VECTORS = {
    "0000000000000000": "0",
    "8000000000000000": "0",
    "0000000000000001": "5e-324",
    "8000000000000001": "-5e-324",
    "7fefffffffffffff": "1.7976931348623157e+308",
    "ffefffffffffffff": "-1.7976931348623157e+308",
    "4340000000000000": "9007199254740992",
    "c340000000000000": "-9007199254740992",
    "4430000000000000": "295147905179352830000",
    "44b52d02c7e14af5": "9.999999999999997e+22",
    "44b52d02c7e14af6": "1e+23",
    "44b52d02c7e14af7": "1.0000000000000001e+23",
    "444b1ae4d6e2ef4e": "999999999999999700000",
    "444b1ae4d6e2ef4f": "999999999999999900000",
    "444b1ae4d6e2ef50": "1e+21",
    "3eb0c6f7a0b5ed8c": "9.999999999999997e-7",
    "3eb0c6f7a0b5ed8d": "0.000001",
    "41b3de4355555553": "333333333.3333332",
    "41b3de4355555554": "333333333.33333325",
    "41b3de4355555555": "333333333.3333333",
    "41b3de4355555556": "333333333.3333334",
    "41b3de4355555557": "333333333.33333343",
    "becbf647612f3696": "-0.0000033333333333333333",
    "43143ff3c1cb0959": "1424953923781206.2",
}


def test_rfc8785_appendix_b_ieee754_boundaries(tmp_path: Path) -> None:
    for hex_bits, expected_token in _APPENDIX_B_VECTORS.items():
        value = struct.unpack(">d", bytes.fromhex(hex_bits))[0]
        canonical = '{"value":' + expected_token + "}"
        _run_and_expect(tmp_path, f"ieee754-{hex_bits}.json", {"value": value}, canonical)


# --- Appendix B：非 finite 值必須 fail closed，不得產生一個雜湊 ----------------


def test_rfc8785_nan_fails_closed(tmp_path: Path) -> None:
    value = struct.unpack(">d", bytes.fromhex("7fffffffffffffff"))[0]
    path = tmp_path / "ieee754-nan.json"
    path.write_text(json.dumps({"value": value}), encoding="utf-8")

    result = run_cli("contract-hash", str(path))

    assert result.returncode != 0
    assert "expected" not in result.stdout


def test_rfc8785_infinity_fails_closed(tmp_path: Path) -> None:
    value = struct.unpack(">d", bytes.fromhex("7ff0000000000000"))[0]
    path = tmp_path / "ieee754-infinity.json"
    path.write_text(json.dumps({"value": value}), encoding="utf-8")

    result = run_cli("contract-hash", str(path))

    assert result.returncode != 0
    assert "expected" not in result.stdout
