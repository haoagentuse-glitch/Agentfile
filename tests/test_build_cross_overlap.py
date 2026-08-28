"""每個輸出 profile 都必須避開所有 profile 的來源 layer。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _layer(path: Path) -> None:
    (path / ".agents/skills/probe").mkdir(parents=True)
    (path / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
    (path / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (path / ".agents/skills/probe/SKILL.md").write_text(
        "---\nname: probe\ndescription: probe\n---\n",
        encoding="utf-8",
    )


def test_output_cannot_overlap_another_profiles_source(tmp_path: Path) -> None:
    _layer(tmp_path / "base")
    source = tmp_path / "generated"
    _layer(source)
    sentinel = source / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    config = tmp_path / "agentfile.toml"
    config.write_text(
        '[profiles.generated]\nlayers = ["base"]\n'
        '[profiles.other]\nlayers = ["generated"]\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentfile",
            "build",
            "--config",
            str(config),
            "--output",
            str(tmp_path),
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "輸出與來源 layer 重疊" in result.stdout
    assert sentinel.read_text(encoding="utf-8") == "keep"
