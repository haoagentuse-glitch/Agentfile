"""從宣告式 layers 建立完整、無執行期繼承的 profile。"""

from __future__ import annotations

import filecmp
import re
import shutil
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BuildError(Exception):
    pass


@dataclass(frozen=True)
class BuildResult:
    profile: str
    output: Path
    files: int


def _validate_profile_name(name: str) -> None:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) is None:
        raise BuildError(
            f"profile 名稱只能使用英數字、點、底線與連字號：{name!r}"
        )


def _profile_layers(
    name: str,
    profiles: dict[str, Any],
    stack: tuple[str, ...] = (),
) -> list[str]:
    if name in stack:
        raise BuildError(f"profile 繼承成環：{' → '.join((*stack, name))}")
    raw = profiles.get(name)
    if not isinstance(raw, dict):
        raise BuildError(f"找不到 profile：{name}")
    layers: list[str] = []
    parent = raw.get("extends")
    if parent is not None:
        if not isinstance(parent, str):
            raise BuildError(f"profiles.{name}.extends 必須是字串")
        layers.extend(_profile_layers(parent, profiles, (*stack, name)))
    own = raw.get("layers")
    if not isinstance(own, list) or not all(isinstance(item, str) for item in own):
        raise BuildError(f"profiles.{name}.layers 必須是字串陣列")
    layers.extend(own)
    return layers


def _instruction_fragments(layer: Path, name: str) -> list[Path]:
    return sorted(path for path in layer.glob(f"{name}*.md") if path.is_file())


def _copy_layer(layer: Path, staging: Path) -> None:
    fragments = {
        *_instruction_fragments(layer, "AGENTS"),
        *_instruction_fragments(layer, "CLAUDE"),
    }
    for source in sorted(layer.rglob("*")):
        if not source.is_file() or source in fragments:
            continue
        relative = source.relative_to(layer)
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if filecmp.cmp(source, target, shallow=False):
                continue
            raise BuildError(f"layer 檔案碰撞：{relative}")
        shutil.copy2(source, target)


def _write_instructions(
    layers: list[Path],
    staging: Path,
    name: str,
) -> None:
    fragments = [
        fragment
        for layer in layers
        for fragment in _instruction_fragments(layer, name)
    ]
    if not fragments:
        raise BuildError(f"profile 缺少 {name} 指令來源")
    body = "\n\n".join(
        fragment.read_text(encoding="utf-8").rstrip() for fragment in fragments
    )
    (staging / f"{name}.md").write_text(body + "\n", encoding="utf-8")


def _mirror_skills(staging: Path) -> None:
    agents_skills = staging / ".agents" / "skills"
    if not agents_skills.is_dir():
        raise BuildError("profile 缺少 .agents/skills")
    claude_skills = staging / ".claude" / "skills"
    if claude_skills.exists():
        raise BuildError("來源不得直接提供 .claude/skills；它由 build 實體複製")
    claude_skills.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(agents_skills, claude_skills)


def _load_config(config_path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = config_path.resolve()
    try:
        data = tomllib.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise BuildError(f"無法讀取 {config_path}：{error}") from error
    profiles = data.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise BuildError("agentfile.toml 缺少 profiles")
    return resolved.parent, data


def build_distributions(
    config_path: Path,
    output_override: Path | None = None,
) -> list[BuildResult]:
    root, config = _load_config(config_path)
    profiles: dict[str, Any] = config["profiles"]
    configured_output = config.get("build", {}).get("output", "dist")
    output = (
        output_override.resolve()
        if output_override is not None
        else (root / configured_output).resolve()
    )
    output.mkdir(parents=True, exist_ok=True)

    results: list[BuildResult] = []
    for profile in profiles:
        _validate_profile_name(profile)
        layer_names = _profile_layers(profile, profiles)
        layers = [(root / name).resolve() for name in layer_names]
        missing = [str(path) for path in layers if not path.is_dir()]
        if missing:
            raise BuildError(f"profile {profile} 缺少 layer：{', '.join(missing)}")

        with tempfile.TemporaryDirectory(prefix=f".{profile}-", dir=output) as temp:
            staging = Path(temp) / profile
            staging.mkdir()
            for layer in layers:
                _copy_layer(layer, staging)
            _write_instructions(layers, staging, "AGENTS")
            _write_instructions(layers, staging, "CLAUDE")
            _mirror_skills(staging)

            target = output / profile
            if target.exists():
                shutil.rmtree(target)
            staging.rename(target)
        files = sum(1 for path in target.rglob("*") if path.is_file())
        results.append(BuildResult(profile, target, files))
    return results
