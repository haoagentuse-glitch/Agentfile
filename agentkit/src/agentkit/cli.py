"""agentkit — structured history of agent sessions for a git repo.

Every subcommand is registered in `build_parser`; `--help` is the full list.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from agentkit import db
from agentkit.capture import parse_transcript
from agentkit.paths import (
    NotAGitRepo,
    agentkit_dir,
    db_path,
    export_dir,
    head_commit,
    transcripts_dir,
)


def cmd_init(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    store = db_path(cwd)
    if store.exists():
        print(f"已初始化：{store}")
        return 0
    db.create(store)
    print(f"已建立：{store}")
    print(f"逐字稿封存：{agentkit_dir(cwd) / 'transcripts'}")
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    payload = json.load(sys.stdin)
    transcript = Path(payload["transcript_path"])
    cwd = Path(payload.get("cwd") or Path.cwd())

    store = db_path(cwd)
    if not store.exists():
        print(f"錯誤：尚未初始化，請先跑 `agentkit init`（預期位置 {store}）", file=sys.stderr)
        return 2
    if not transcript.exists():
        print(f"錯誤：找不到逐字稿 {transcript}", file=sys.stderr)
        return 2

    parsed = parse_transcript(transcript)
    session_id = parsed.session.session_id or payload.get("session_id")

    archive = transcripts_dir(cwd, parsed.session.agent) / f"{session_id}.jsonl"
    archive.parent.mkdir(parents=True, exist_ok=True)
    # Re-ingesting from the archive is how a store gets rebuilt; then there is
    # nothing to copy and the source is already where it belongs.
    if not (archive.exists() and archive.samefile(transcript)):
        shutil.copy2(transcript, archive)

    record = {
        "session_id": session_id,
        "agent": parsed.session.agent,
        "model": parsed.session.model,
        "title": parsed.session.title,
        "branch": parsed.session.branch,
        "worktree": str(cwd),
        "cwd": parsed.session.cwd,
        "started_at": parsed.session.started_at,
        "ended_at": parsed.session.ended_at,
        "transcript_path": str(archive),
        "commit_sha": head_commit(cwd),
    }
    with db.connect(store) as conn:
        db.upsert_session(conn, record, parsed.messages, parsed.tool_calls, parsed.changed_files)

    print(f"已擷取 {session_id}，來源 {transcript}")
    print(
        f"  {len(parsed.messages)} 則訊息、{len(parsed.tool_calls)} 次工具呼叫、"
        f"{len(parsed.changed_files)} 個變更檔案"
    )
    print(f"  已封存至 {archive}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    store = db_path(cwd)
    if not store.exists():
        print(f"錯誤：尚未初始化，請先跑 `agentkit init`（預期位置 {store}）", file=sys.stderr)
        return 2

    with db.connect(store) as conn:
        rows = db.recent_sessions(conn, limit=args.limit)

    print(f"資料庫：{store}")
    print(f"commit：{head_commit(cwd) or '（尚無 commit）'}")
    if not rows:
        print("尚未擷取任何 session")
        return 0

    print(f"最近 {len(rows)} 個 session：")
    for row in rows:
        print(
            f"  {row['session_id']}  {row['agent']}/{row['model']}  "
            f"{row['branch']}  {row['ended_at']}  "
            f"{row['changed_count']} 個變更檔案  {row['title'] or ''}".rstrip()
        )
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    store = db_path(cwd)
    if not store.exists():
        print(f"錯誤：尚未初始化，請先跑 `agentkit init`（預期位置 {store}）", file=sys.stderr)
        return 2

    with db.connect(store) as conn:
        rows = db.search_messages(conn, args.query, limit=args.limit)

    print(f"資料庫：{store}")
    print(f"查詢：{args.query!r}")
    if not rows:
        print("沒有符合的訊息")
        return 0

    print(f"{len(rows)} 筆：")
    for row in rows:
        snippet = " ".join(row["text"].split())
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"
        print(f"\n  {row['session_id']}  {row['role']}  {row['timestamp']}")
        print(f"  {snippet}")
    return 0


def _session_markdown(session: dict, messages, changed_files) -> str:
    """One session as Markdown. Headings per message so a chunker has seams to cut on."""
    head = session["title"] or session["session_id"]
    lines = [
        f"# {head}",
        "",
        f"- session: `{session['session_id']}`",
        f"- agent: {session['agent']} / {session['model']}",
        f"- branch: {session['branch']}",
        f"- 期間: {session['started_at']} → {session['ended_at']}",
        f"- commit: {session['commit_sha']}",
    ]
    lines.append("")
    for msg in messages:
        lines += [f"## {msg['role']} · {msg['timestamp']}", "", msg["text"], ""]
    if changed_files:
        # Own heading, own chunk: a wall of paths would otherwise dilute the
        # embedding of whatever chunk it landed in.
        lines += ["## 變更檔案", ""]
        lines += [f"- `{p}`" for p in changed_files]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def cmd_export(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    store = db_path(cwd)
    if not store.exists():
        print(f"錯誤：尚未初始化，請先跑 `agentkit init`（預期位置 {store}）", file=sys.stderr)
        return 2

    target = Path(args.markdown) if args.markdown else export_dir(cwd)
    target.mkdir(parents=True, exist_ok=True)

    with db.connect(store) as conn:
        sessions = db.all_sessions(conn)
        written = []
        for row in sessions:
            session = dict(row)
            sid = session["session_id"]
            text = _session_markdown(
                session, db.messages_of(conn, sid), db.changed_files_of(conn, sid)
            )
            # A projection, never a merge: whatever is there is replaced.
            path = target / f"{sid}.md"
            path.write_text(text, encoding="utf-8")
            written.append(path)

    print(f"已輸出 {len(written)} 個 session 至 {target}")
    for path in written:
        print(f"  {path}")
    print("這是可重建的投影，手改沒有意義——下次 export 會直接覆蓋")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check the things that silently break capture. Structured history only —
    the semantic layer is a separate, swappable concern and is not checked here."""
    cwd = Path.cwd()
    root = agentkit_dir(cwd)
    store = db_path(cwd)
    checks: list[tuple[bool, str]] = []

    writable = root.parent.exists() and os.access(root.parent, os.W_OK)
    checks.append((writable, f"共用 git 目錄可寫入：{root.parent}"))
    checks.append((store.exists(), f"資料庫存在（否則請跑 `agentkit init`）：{store}"))

    if store.exists():
        with db.connect(store) as conn:
            names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master")}
        missing = {"sessions", "messages", "tool_calls", "changed_files"} - names
        detail = (
            "schema 完整"
            if not missing
            else f"schema 不完整，缺少 {missing}；請刪除 {store} 後重跑 `init`"
        )
        checks.append((not missing, detail))

    settings = cwd / ".claude" / "settings.json"
    hooked = settings.exists() and "agentkit capture" in settings.read_text()
    checks.append((hooked, f"SessionEnd hook 已註冊於 {settings}"))

    for ok, label in checks:
        print(f"  {'通過' if ok else '失敗'} {label}")
    failed = [label for ok, label in checks if not ok]
    print(f"{len(checks) - len(failed)}/{len(checks)} 項檢查通過")
    return 0 if not failed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentkit", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create the store for this repo (idempotent)")
    init.set_defaults(func=cmd_init)

    capture = sub.add_parser("capture", help="ingest a finished session (called by the hook)")
    capture.add_argument(
        "--stdin", action="store_true", help="read the hook payload as JSON on stdin"
    )
    capture.set_defaults(func=cmd_capture)

    status = sub.add_parser("status", help="what has been captured for this repo")
    status.add_argument("--limit", type=int, default=10, help="how many sessions to show")
    status.set_defaults(func=cmd_status)

    search = sub.add_parser("search", help="substring search over what was said")
    search.add_argument("query", help="text to look for; any length, any script")
    search.add_argument("--limit", type=int, default=20, help="how many matches to show")
    search.set_defaults(func=cmd_search)

    export = sub.add_parser("export", help="project the store to Markdown for external indexers")
    export.add_argument(
        "--markdown",
        nargs="?",
        const="",
        metavar="DIR",
        help="output directory; omit the value for <git-common-dir>/agentkit/export/",
    )
    export.set_defaults(func=cmd_export)

    doctor = sub.add_parser("doctor", help="check the things that silently break capture")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except NotAGitRepo as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
