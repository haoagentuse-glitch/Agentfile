"""建置必須在修改輸出前拒絕來源重疊與路徑型別碰撞。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(config: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "agentfile",
            "build",
            "--config",
            str(config),
            "--output",
            str(output),
        ],
        cwd=config.parent,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
    )


def _instructions(layer: Path) -> None:
    (layer / ".agents/skills/probe").mkdir(parents=True)
    (layer / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
    (layer / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (layer / ".agents/skills/probe/SKILL.md").write_text(
        "---\nname: probe\ndescription: probe\n---\n",
        encoding="utf-8",
    )


def test_output_profile_cannot_overlap_a_source_layer(tmp_path: Path) -> None:
    layer = tmp_path / "source"
    _instructions(layer)
    sentinel = layer / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    config = tmp_path / "agentfile.toml"
    config.write_text('[profiles.source]\nlayers = ["source"]\n', encoding="utf-8")

    result = _run(config, tmp_path)

    assert result.returncode == 2
    assert "輸出與來源 layer 重疊" in result.stdout
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_file_directory_collision_is_a_controlled_error(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _instructions(first)
    (second / "nested/child").mkdir(parents=True)
    (first / "nested").write_text("file", encoding="utf-8")
    (second / "nested/child/value.txt").write_text("value", encoding="utf-8")
    config = tmp_path / "agentfile.toml"
    config.write_text(
        '[profiles.test]\nlayers = ["first", "second"]\n',
        encoding="utf-8",
    )

    result = _run(config, tmp_path / "dist")

    assert result.returncode == 2
    assert "layer 路徑型別碰撞" in result.stdout
