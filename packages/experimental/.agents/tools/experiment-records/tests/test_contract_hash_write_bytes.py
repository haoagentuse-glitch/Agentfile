"""`contract-hash --write` 只能動 contract_hash 這一個欄位的值。

其餘位元組（縮排、key 順序、緊湊格式、其他欄位裡剛好寫著 "contract_hash" 這幾個字的
內容）一律原樣保留。用手寫的原始 JSON 文字直接做位元組級比對，不透過
`json.dumps` 重新序列化再比對結構——結構相等蓋不住格式被整檔重寫的問題。
"""

from __future__ import annotations

import re
from pathlib import Path

from helpers import run_cli


def _expected_hash(path: Path) -> str:
    verify = run_cli("contract-hash", str(path))
    match = re.search(r"^expected：(\S+)$", verify.stdout, re.MULTILINE)
    assert match, verify.stdout + verify.stderr
    return match.group(1)


def test_write_preserves_compact_formatting(tmp_path: Path) -> None:
    path = tmp_path / "compact.json"
    before = '{"a":1,"contract_hash":"WRONG","b":2}'
    path.write_text(before, encoding="utf-8")
    expected = _expected_hash(path)

    result = run_cli("contract-hash", str(path), "--write")

    assert result.returncode == 0, result.stdout + result.stderr
    after = path.read_text(encoding="utf-8")
    assert after == before.replace('"contract_hash":"WRONG"', f'"contract_hash":"{expected}"')


def test_write_preserves_bytes_when_field_is_not_first(tmp_path: Path) -> None:
    path = tmp_path / "non-first.json"
    before = '{\n  "a": 1,\n  "contract_hash": "WRONG",\n  "b": 2\n}\n'
    path.write_text(before, encoding="utf-8")
    expected = _expected_hash(path)

    result = run_cli("contract-hash", str(path), "--write")

    assert result.returncode == 0, result.stdout + result.stderr
    after = path.read_text(encoding="utf-8")
    assert after == before.replace('"contract_hash": "WRONG"', f'"contract_hash": "{expected}"')
    # key 順序不變：a 仍在 contract_hash 之前、b 仍在之後。
    assert after.index('"a"') < after.index('"contract_hash"') < after.index('"b"')


def test_write_ignores_decoy_occurrences_of_the_field_name(tmp_path: Path) -> None:
    """字串內容裡剛好出現 "contract_hash" 字樣、巢狀 object 裡剛好有同名鍵，
    都不是頂層那個欄位，寫入時不得被誤配對或被動到。"""
    path = tmp_path / "decoy.json"
    before = (
        '{"note":"see contract_hash for details",'
        '"meta":{"contract_hash":"nested-should-not-move"},'
        '"contract_hash":"WRONG",'
        '"a":1}'
    )
    path.write_text(before, encoding="utf-8")
    expected = _expected_hash(path)

    result = run_cli("contract-hash", str(path), "--write")

    assert result.returncode == 0, result.stdout + result.stderr
    after = path.read_text(encoding="utf-8")
    expected_after = before.replace(
        '"contract_hash":"WRONG"', f'"contract_hash":"{expected}"'
    )
    assert after == expected_after
    # 兩個 decoy 一字不動：字串內容與巢狀鍵的值都還是原樣。
    assert '"note":"see contract_hash for details"' in after
    assert '"meta":{"contract_hash":"nested-should-not-move"}' in after


def test_write_inserts_field_when_absent_without_touching_existing_bytes(tmp_path: Path) -> None:
    path = tmp_path / "absent.json"
    before = '{\n  "a": 1,\n  "b": 2\n}\n'
    path.write_text(before, encoding="utf-8")
    expected = _expected_hash(path)

    result = run_cli("contract-hash", str(path), "--write")

    assert result.returncode == 0, result.stdout + result.stderr
    after = path.read_text(encoding="utf-8")
    # 新增的欄位之前，原有內容一字不動。
    assert after.startswith('{\n  "a": 1,\n  "b": 2')
    assert f'"contract_hash":"{expected}"' in after
