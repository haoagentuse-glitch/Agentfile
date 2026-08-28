"""agentfile 的公開命令列入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

from agentfile.distribution import BuildError, build_distributions


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="agentfile")
    commands = root.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="產生可直接複製的完整 profile")
    build.add_argument("--config", default="agentfile.toml")
    build.add_argument("--output")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command != "build":
        raise AssertionError(args.command)
    try:
        results = build_distributions(
            Path(args.config),
            Path(args.output) if args.output else None,
        )
    except BuildError as error:
        print(f"ERROR：{error}")
        return 2
    for result in results:
        print(f"{result.profile}：{result.files} 個檔案 → {result.output}")
    return 0
