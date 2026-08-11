"""公開入口：`python -m experiment_records <subcommand>`。目前只有 `validate`。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from experiment_records.project_layout import ProjectLayoutError, collect_targets, resolve_layout
from experiment_records.validation import validate_record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m experiment_records",
        description="驗證 records/experiments/ 底下的實驗紀錄：完整 JSON Schema "
        "Draft 2020-12 驗證 + project-root-relative ref 邊界檢查。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate_p = sub.add_parser(
        "validate",
        help="對 project root、records/experiments root 或單一 record 檔案跑驗證",
    )
    validate_p.add_argument(
        "target",
        help="project root、records/experiments 目錄，或單一 record 的 JSON 檔案路徑",
    )

    return parser


def _cmd_validate(target_arg: str) -> int:
    target = Path(target_arg)
    resolved = target if target.is_absolute() else Path.cwd() / target
    if not resolved.exists():
        print(f"找不到路徑：{target_arg}", file=sys.stderr)
        return 2
    resolved = resolved.resolve()

    try:
        layout = resolve_layout(resolved)
        targets = collect_targets(resolved, layout)
    except ProjectLayoutError as e:
        print(str(e), file=sys.stderr)
        return 2

    if not targets:
        print("沒有找到任何 record 可驗證。")
        return 0

    error_count = 0
    for record_path in targets:
        for level, message in validate_record(record_path, layout):
            print(f"{level:5s} {message}")
            if level == "ERROR":
                error_count += 1

    print()
    print(f"已檢查 {len(targets)} 筆紀錄，發現 {error_count} 個錯誤。")
    return 1 if error_count else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _cmd_validate(args.target)

    parser.error(f"未知指令：{args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
