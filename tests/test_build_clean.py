"""發行包不得攜帶來源 layer 內的本機衍生目錄。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = {
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "target",
}


def test_build_excludes_generated_directories(tmp_path: Path) -> None:
    layer = tmp_path / "layer"
    (layer / ".agents/skills/probe").mkdir(parents=True)
    (layer / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
    (layer / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (layer / ".agents/skills/probe/SKILL.md").write_text(
        "---\nname: probe\ndescription: probe\n---\n",
        encoding="utf-8",
    )
    for directory in GENERATED:
        generated = layer / directory
        generated.mkdir()
        (generated / "local.txt").write_text("local", encoding="utf-8")
    config = tmp_path / "agentfile.toml"
    config.write_text('[profiles.test]\nlayers = ["layer"]\n', encoding="utf-8")
    output = tmp_path / "dist"

    result = subprocess.run(
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
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    built_parts = {
        part
        for path in (output / "test").rglob("*")
        for part in path.relative_to(output / "test").parts
    }
    assert built_parts.isdisjoint(GENERATED)
