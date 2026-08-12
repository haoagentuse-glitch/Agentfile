"""版本化 prompt role：內容雜湊可機械比對，輸出型別固定，且無權改閘門狀態。

prompt 是最常被當成隱藏設定的東西。內容改了、輸出跟著變，但沒有任何欄位記錄這件事——
prompt_hash 就是為了讓這件事留下痕跡。
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from helpers import run_cli, valid_definition, write_config, write_record

EXPECTED_ROLES = {
    "question-builder@1",
    "counterexample-reviewer@1",
    "experiment-design-critic@1",
    "failure-diagnoser@1",
    "claim-writer@1",
    "evidence-reviewer@1",
}


def _find(relative: str) -> Path:
    for candidate in Path(__file__).resolve().parents:
        probe = candidate / relative
        if probe.exists():
            return probe
    raise RuntimeError(f"找不到 {relative}")


PROMPTS = _find("records/experiments/prompts")
PROMPT_OUTPUT_SCHEMA = json.loads(
    (_find("records/experiments/schemas") / "prompt-output.schema.json").read_text(encoding="utf-8")
)


def _digest(prompt_id: str) -> str:
    return "sha256:" + hashlib.sha256((PROMPTS / f"{prompt_id}.md").read_bytes()).hexdigest()


@pytest.fixture
def project_with_prompts(project: Path) -> Path:
    shutil.copytree(PROMPTS, project / "records" / "experiments" / "prompts")
    write_config(project, "records/experiments/configs/baseline.yaml")
    write_config(project, "records/experiments/configs/treatment.yaml")
    return project


def _producer(prompt_id: str, prompt_hash: str | None) -> dict:
    producer = {
        "kind": "software_agent",
        "name": prompt_id.split("@")[0],
        "model": "anthropic/claude-opus-5",
        "prompt_id": prompt_id,
        "created_at": "2026-01-01T00:00:00Z",
    }
    if prompt_hash is not None:
        producer["prompt_hash"] = prompt_hash
    return producer


def test_all_six_roles_exist() -> None:
    assert {path.stem for path in PROMPTS.glob("*.md")} == EXPECTED_ROLES


def test_every_role_has_a_typed_output_definition() -> None:
    """每個 role 的輸出都要有型別，不是自由格式的 JSON。"""
    defs = PROMPT_OUTPUT_SCHEMA["$defs"]
    for role in EXPECTED_ROLES:
        camel = "".join(
            part if index == 0 else part.capitalize()
            for index, part in enumerate(role.split("@")[0].split("-"))
        )
        assert f"{camel}Output" in defs, f"{role} 沒有對應的輸出型別"


def test_no_role_output_can_touch_gate_or_lifecycle_state() -> None:
    """提示詞提出候選與批評；閘門、比較判定與狀態轉移由確定性程式負責。

    這條界線寫在 schema 裡，不只寫在提示詞裡——提示詞可以被忽略，schema 不行。
    """
    forbidden = {
        "gate_level", "current_level", "gate_status", "request_level",
        "comparison_valid", "confounded", "to_state", "from_state",
        "lifecycle_state", "final_verdict", "mechanical_pass",
    }

    def walk(node: object) -> set[str]:
        found: set[str] = set()
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "properties" and isinstance(value, dict):
                    found |= forbidden & set(value)
                found |= walk(value)
        elif isinstance(node, list):
            for item in node:
                found |= walk(item)
        return found

    assert walk(PROMPT_OUTPUT_SCHEMA["$defs"]) == set()


def test_prompts_subcommand_lists_every_role_with_its_hash(project_with_prompts: Path) -> None:
    result = run_cli("prompts", str(project_with_prompts))

    assert result.returncode == 0, result.stdout + result.stderr
    for role in EXPECTED_ROLES:
        assert role in result.stdout
        assert _digest(role) in result.stdout


def test_prompts_subcommand_is_honest_when_there_are_no_prompts(project: Path) -> None:
    result = run_cli("prompts", str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "沒有自己管理的 prompt role" in result.stdout


def test_matching_prompt_hash_passes(project_with_prompts: Path) -> None:
    write_record(
        project_with_prompts, "definitions", "demo-exp",
        valid_definition(producer=_producer("question-builder@1", _digest("question-builder@1"))),
    )

    result = run_cli("validate", str(project_with_prompts))

    assert result.returncode == 0, result.stdout + result.stderr


def test_stale_prompt_hash_is_rejected(project_with_prompts: Path) -> None:
    """prompt 改了而 hash 沒改，等於把 prompt 漂移藏起來。"""
    write_record(
        project_with_prompts, "definitions", "demo-exp",
        valid_definition(producer=_producer("question-builder@1", "sha256:" + "0" * 64)),
    )

    result = run_cli("validate", str(project_with_prompts))

    assert result.returncode == 1
    assert "prompt_hash 與 prompts/question-builder@1.md 實際內容不符" in result.stdout


def test_edited_prompt_invalidates_a_previously_matching_hash(project_with_prompts: Path) -> None:
    """這是這個檢查存在的理由：同名 prompt 改了內容就必須被抓到。"""
    digest = _digest("question-builder@1")
    write_record(
        project_with_prompts, "definitions", "demo-exp",
        valid_definition(producer=_producer("question-builder@1", digest)),
    )
    prompt_file = project_with_prompts / "records" / "experiments" / "prompts" / "question-builder@1.md"
    prompt_file.write_text(prompt_file.read_text(encoding="utf-8") + "\n多加一行。\n", encoding="utf-8")

    result = run_cli("validate", str(project_with_prompts))

    assert result.returncode == 1
    assert "prompt_hash 與 prompts/question-builder@1.md 實際內容不符" in result.stdout


def test_missing_prompt_hash_warns_but_does_not_fail(project_with_prompts: Path) -> None:
    write_record(
        project_with_prompts, "definitions", "demo-exp",
        valid_definition(producer=_producer("question-builder@1", None)),
    )

    result = run_cli("validate", str(project_with_prompts))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "沒有記錄 prompt_hash" in result.stdout


def test_prompt_not_managed_here_is_skipped(project_with_prompts: Path) -> None:
    """專案可以用自己的 prompt。不能驗證的東西不假裝驗證過。"""
    write_record(
        project_with_prompts, "definitions", "demo-exp",
        valid_definition(producer=_producer("some-house-prompt@7", "sha256:" + "1" * 64)),
    )

    result = run_cli("validate", str(project_with_prompts))

    assert result.returncode == 0, result.stdout + result.stderr


def test_prompts_directory_is_not_validated_as_records(project_with_prompts: Path) -> None:
    """prompts/ 跟 configs/ 一樣是輔助資料，不是 record 類型。"""
    result = run_cli("validate", str(project_with_prompts))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "無法辨識 record 類型" not in result.stdout
