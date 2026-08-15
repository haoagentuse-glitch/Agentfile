"""公開入口：`python -m experiment_records <subcommand>`。"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiment_records import claim_audit, compare_runs, compute_gate
from experiment_records.project_layout import (
    ProjectLayoutError,
    collect_targets,
    record_type_for,
    resolve_layout,
)
from experiment_records.prompts import known_prompts, prompts_dir
from experiment_records.review_package import ReviewPackageError, build_review_package
from experiment_records.validation import (
    schema_count,
    validate_claim_audit_chain,
    validate_lifecycle_candidate,
    validate_lifecycle_events,
    validate_lifecycle_history_candidate,
    validate_record,
    validate_run_lineage,
    validate_schemas,
)

DETERMINISTIC_COMMANDS: dict[str, tuple[str, Callable[[list[str] | None], int]]] = {
    "compare-runs": ("比較兩個 run；先判可比較性再計算差異", compare_runs.main),
    "claim-audit": ("機械核對 claim 的引用、方向與幅度", claim_audit.main),
    "compute-gate": ("依 Contract 的凍結門檻判定算力升級", compute_gate.main),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m experiment_records",
        description="驗證實驗 record，並以不可覆寫方式新增生命週期事件。",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate", help="驗證 project root、records root 或單一 record")
    validate_parser.add_argument("target", help="project root、records/experiments 或單一 JSON record")

    transition_parser = sub.add_parser("transition", help="新增一個不可變生命週期 transition event")
    transition_parser.add_argument("project", help="project root 或 records/experiments")
    transition_parser.add_argument("experiment_id")
    transition_parser.add_argument("to_state")
    transition_parser.add_argument("--reason", required=True)
    transition_parser.add_argument("--evidence-ref", action="append", default=[])
    transition_parser.add_argument("--updated-definition-field", action="append", default=[])
    transition_parser.add_argument("--occurred-at", help="RFC 3339 timestamp。省略時使用目前 UTC 時間")

    prompts_parser = sub.add_parser("prompts", help="列出本專案管理的 prompt role 與內容雜湊")
    prompts_parser.add_argument("project", help="project root 或 records/experiments")

    review_parser = sub.add_parser("review-package", help="組出獨立審核者收到的完整輸入")
    review_parser.add_argument("project", help="project root 或 records/experiments")
    review_parser.add_argument("claim_id")
    review_parser.add_argument("--output", help="寫出的路徑；不給就印到標準輸出")
    for name, (help_text, _) in DETERMINISTIC_COMMANDS.items():
        sub.add_parser(name, help=help_text, add_help=False)
    return parser


def _git_commit(project_root: Path) -> str:
    try:
        head = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--verify", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        status = subprocess.run(
            ["git", "-C", str(project_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "無法取得"
    if head.returncode == 0 and head.stdout.strip():
        suffix = "-dirty" if status.returncode != 0 or status.stdout.strip() else ""
        return f"{head.stdout.strip()}{suffix}"
    return "無法取得（不是 Git repo 或尚無 commit）"


def _resolve_target(target_arg: str) -> Path | None:
    target = Path(target_arg)
    resolved = target if target.is_absolute() else Path.cwd() / target
    if not resolved.exists():
        print(f"找不到路徑：{target_arg}", file=sys.stderr)
        return None
    return resolved.resolve()


def _all_results(targets: list[Path], layout: Any) -> list[tuple[str, str]]:
    results = validate_schemas(layout)
    if any(level == "錯誤" for level, _ in results):
        return results
    for path in targets:
        results.extend(validate_record(path, layout))
    results.extend(validate_run_lineage(targets, layout))
    results.extend(validate_claim_audit_chain(targets, layout))
    results.extend(validate_lifecycle_events(targets, layout))
    return results


def _cmd_validate(target_arg: str) -> int:
    resolved = _resolve_target(target_arg)
    if resolved is None:
        return 2
    try:
        layout = resolve_layout(resolved)
        targets = collect_targets(resolved, layout)
    except ProjectLayoutError as error:
        print(str(error), file=sys.stderr)
        return 2

    print("命令：uv run --project .agents/tools/experiment-records python -m experiment_records validate")
    print(f"輸入：{resolved}")
    print(f"Schema：{layout.schemas_dir}")
    print(f"Commit：{_git_commit(layout.project_root)}")
    print()

    schema_results = validate_schemas(layout)
    results = list(schema_results)
    if not any(level == "錯誤" for level, _ in schema_results):
        for path in targets:
            results.extend(validate_record(path, layout))
        if not resolved.is_file():
            results.extend(validate_run_lineage(targets, layout))
            results.extend(validate_claim_audit_chain(targets, layout))
            results.extend(validate_lifecycle_events(targets, layout))

    for level, message in results:
        print(f"{level:5s} {message}")
    error_count = sum(level == "錯誤" for level, _ in results)
    if not targets and not error_count:
        print("沒有找到任何 record 可驗證。")
    print()
    record_count = 0 if any(level == "錯誤" for level, _ in schema_results) else len(targets)
    print(f"已檢查 {schema_count()} 份 Schema、{record_count} 筆紀錄，發現 {error_count} 個錯誤。")
    return 1 if error_count else 0


def _load_experiment_events(targets: list[Path], experiment_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in targets:
        if record_type_for(path) != "lifecycles":
            continue
        event = json.loads(path.read_text(encoding="utf-8"))
        if event.get("experiment_id") == experiment_id:
            events.append(event)
    return sorted(events, key=lambda event: event["sequence"])


def _cmd_transition(args: argparse.Namespace) -> int:
    resolved = _resolve_target(args.project)
    if resolved is None:
        return 2
    try:
        layout = resolve_layout(resolved)
        targets = collect_targets(resolved, layout)
    except ProjectLayoutError as error:
        print(str(error), file=sys.stderr)
        return 2

    occurred_at = args.occurred_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    command = [
        "uv", "run", "--project", ".agents/tools/experiment-records", "python", "-m",
        "experiment_records", "transition", str(resolved), args.experiment_id, args.to_state,
        "--reason", args.reason, "--occurred-at", occurred_at,
    ]
    for evidence_ref in args.evidence_ref:
        command.extend(["--evidence-ref", evidence_ref])
    for field in args.updated_definition_field:
        command.extend(["--updated-definition-field", field])
    print(f"命令：{shlex.join(command)}")
    print(f"輸入：experiment_id={args.experiment_id}，to_state={args.to_state}")
    print(f"Schema：{layout.schemas_dir}")
    print(f"Commit：{_git_commit(layout.project_root)}")
    print(f"設定：reason={args.reason!r}，occurred_at={occurred_at}")
    print(f"Evidence：{args.evidence_ref}")
    print(f"Definition fields：{args.updated_definition_field}")
    print()
    existing_results = _all_results(targets, layout)
    existing_errors = [message for level, message in existing_results if level == "錯誤"]
    if existing_errors:
        print("現有 project 驗證失敗。未建立 event。", file=sys.stderr)
        for message in existing_errors:
            print(f"錯誤    {message}", file=sys.stderr)
        return 1

    events = _load_experiment_events(targets, args.experiment_id)
    sequence = len(events) + 1
    from_state = events[-1]["to_state"] if events else None
    event: dict[str, Any] = {
        "event_id": f"{args.experiment_id}-{sequence:04d}",
        "experiment_id": args.experiment_id,
        "sequence": sequence,
        "from_state": from_state,
        "to_state": args.to_state,
        "occurred_at": occurred_at,
        "reason": args.reason,
        "evidence_refs": args.evidence_ref,
    }
    if args.updated_definition_field:
        event["updated_definition_fields"] = args.updated_definition_field

    output_dir = layout.records_root / "lifecycles"
    output_path = output_dir / f"{args.experiment_id}-{sequence:04d}.json"
    label = str(output_path.relative_to(layout.project_root))
    candidate_results = validate_lifecycle_candidate(event, label, layout)
    candidate_results.extend(validate_lifecycle_history_candidate(events, event, label, layout))
    errors = [message for level, message in candidate_results if level == "錯誤"]
    if errors:
        for message in errors:
            print(f"錯誤    {message}", file=sys.stderr)
        print("未建立 event。", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("x", encoding="utf-8") as output:
            json.dump(event, output, ensure_ascii=False, indent=2)
            output.write("\n")
    except FileExistsError:
        print(f"event 已存在，拒絕覆寫：{output_path}", file=sys.stderr)
        return 1

    print(f"輸出：{output_path}")
    print(f"轉移：{from_state} -> {args.to_state}")
    return 0


def _cmd_prompts(project_arg: str) -> int:
    """把 prompt_hash 從「自己算一次」變成「查一次」。

    要人手動算雜湊，實務上就會有人填錯或不填；填錯會被 validate 擋下，但那時已經
    多繞一圈。這裡直接給可貼進 producer 的值。
    """
    resolved = _resolve_target(project_arg)
    if resolved is None:
        return 2
    try:
        layout = resolve_layout(resolved)
    except ProjectLayoutError as error:
        print(str(error), file=sys.stderr)
        return 2

    command = ["uv", "run", "--project", ".agents/tools/experiment-records", "python", "-m",
               "experiment_records", "prompts", str(resolved)]
    print(f"命令：{shlex.join(command)}")
    print(f"輸入：{resolved}")
    print(f"Prompt 目錄：{prompts_dir(layout)}")
    print(f"Commit：{_git_commit(layout.project_root)}")
    print()

    registry = known_prompts(layout)
    if not registry:
        print("這個專案沒有自己管理的 prompt role。")
        print("producer.prompt_hash 沒有可比對的來源，驗證會略過雜湊檢查。")
        return 0

    width = max(len(prompt_id) for prompt_id in registry)
    for prompt_id, digest in registry.items():
        print(f"{prompt_id:{width}s}  {digest}")
    print()
    print(f"共 {len(registry)} 個 prompt role。把 prompt_id 與上面的雜湊一起寫進 producer。")
    return 0


def _cmd_review_package(args: argparse.Namespace) -> int:
    resolved = _resolve_target(args.project)
    if resolved is None:
        return 2
    try:
        layout = resolve_layout(resolved)
    except ProjectLayoutError as error:
        print(str(error), file=sys.stderr)
        return 2

    command = ["uv", "run", "--project", ".agents/tools/experiment-records", "python", "-m",
               "experiment_records", "review-package", str(resolved), args.claim_id]
    if args.output:
        command.extend(["--output", args.output])
    print(f"命令：{shlex.join(command)}")
    print(f"輸入：claim_id={args.claim_id}")
    print(f"Schema：{layout.schemas_dir / 'review-package.schema.json'}")
    print(f"Commit：{_git_commit(layout.project_root)}")
    print()

    try:
        package = build_review_package(layout, args.claim_id)
    except ReviewPackageError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"輸出：{output_path}")
    else:
        print(json.dumps(package, ensure_ascii=False, indent=2))

    unresolved = [e for e in package["evidence_excerpts"] if not e["resolved"]]
    print()
    print(f"審核政策：{package['policy']['required_reviewer_kind']}")
    print(f"證據摘錄：{len(package['evidence_excerpts'])} 筆，其中 {len(unresolved)} 筆取不到值")
    print(f"run 摘要：{len(package['runs'])} 筆（含失敗與作廢）")
    for line in package["omitted"]:
        print(f"未包含：{line}")
    return 0


def main(argv: list[str] | None = None) -> int:
    command_args = sys.argv[1:] if argv is None else argv
    if command_args:
        command = DETERMINISTIC_COMMANDS.get(command_args[0])
        if command is not None:
            _, handler = command
            return handler(command_args[1:])

    parser = build_parser()
    args = parser.parse_args(command_args)
    if args.command == "validate":
        return _cmd_validate(args.target)
    if args.command == "transition":
        return _cmd_transition(args)
    if args.command == "prompts":
        return _cmd_prompts(args.project)
    if args.command == "review-package":
        return _cmd_review_package(args)
    parser.error(f"未知指令：{args.command}")
    return 2
