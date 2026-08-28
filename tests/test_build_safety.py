"""自訂 build 設定必須在輸出邊界內失敗。"""

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


def _minimal_layer(root: Path, name: str) -> Path:
    layer = root / name
    (layer / ".agents/skills/probe").mkdir(parents=True)
    (layer / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
    (layer / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (layer / ".agents/skills/probe/SKILL.md").write_text(
        "---\nname: probe\ndescription: probe\n---\n",
        encoding="utf-8",
    )
    return layer


def test_profile_name_cannot_escape_output_directory(tmp_path: Path) -> None:
    _minimal_layer(tmp_path, "layer")
    output = tmp_path / "dist"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    config = tmp_path / "agentfile.toml"
    config.write_text(
        '[profiles."../outside"]\nlayers = ["layer"]\n',
        encoding="utf-8",
    )

    result = _run(config, output)

    assert result.returncode == 2
    assert "profile 名稱" in result.stdout
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_profile_inheritance_cycle_fails_clearly(tmp_path: Path) -> None:
    config = tmp_path / "agentfile.toml"
    config.write_text(
        '[profiles.a]\nextends = "b"\nlayers = []\n'
        '[profiles.b]\nextends = "a"\nlayers = []\n',
        encoding="utf-8",
    )

    result = _run(config, tmp_path / "dist")

    assert result.returncode == 2
    assert "繼承成環" in result.stdout


def test_different_files_at_the_same_layer_path_fail(tmp_path: Path) -> None:
    first = _minimal_layer(tmp_path, "first")
    second = tmp_path / "second"
    second.mkdir()
    (first / "shared.txt").write_text("first", encoding="utf-8")
    (second / "shared.txt").write_text("second", encoding="utf-8")
    config = tmp_path / "agentfile.toml"
    config.write_text(
        '[profiles.test]\nlayers = ["first", "second"]\n',
        encoding="utf-8",
    )

    result = _run(config, tmp_path / "dist")

    assert result.returncode == 2
    assert "layer 檔案碰撞：shared.txt" in result.stdout
