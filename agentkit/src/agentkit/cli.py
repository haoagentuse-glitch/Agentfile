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
from agentkit.paths import NotAGitRepo, agentkit_dir, db_path, head_commit, transcripts_dir


def cmd_init(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    store = db_path(cwd)
    if store.exists():
        print(f"already initialised: {store}")
        return 0
    db.create(store)
    print(f"initialised: {store}")
    print(f"transcripts: {agentkit_dir(cwd) / 'transcripts'}")
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    payload = json.load(sys.stdin)
    transcript = Path(payload["transcript_path"])
    cwd = Path(payload.get("cwd") or Path.cwd())

    store = db_path(cwd)
    if not store.exists():
        print(f"error: not initialised — run `agentkit init` (expected {store})", file=sys.stderr)
        return 2
    if not transcript.exists():
        print(f"error: transcript not found: {transcript}", file=sys.stderr)
        return 2

    parsed = parse_transcript(transcript)
    session_id = parsed.session.session_id or payload.get("session_id")

    archive = transcripts_dir(cwd, parsed.session.agent) / f"{session_id}.jsonl"
    archive.parent.mkdir(parents=True, exist_ok=True)
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
        db.upsert_session(conn, record, parsed.tool_calls, parsed.changed_files)

    print(f"captured {session_id} from {transcript}")
    print(f"  {len(parsed.tool_calls)} tool calls, {len(parsed.changed_files)} changed files")
    print(f"  archived to {archive}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    store = db_path(cwd)
    if not store.exists():
        print(f"error: not initialised — run `agentkit init` (expected {store})", file=sys.stderr)
        return 2

    with db.connect(store) as conn:
        rows = db.recent_sessions(conn, limit=args.limit)

    print(f"store:  {store}")
    print(f"commit: {head_commit(cwd) or '(no commits)'}")
    if not rows:
        print("no sessions captured yet")
        return 0

    print(f"{len(rows)} most recent session(s):")
    for row in rows:
        print(
            f"  {row['session_id']}  {row['agent']}/{row['model']}  "
            f"{row['branch']}  {row['ended_at']}  "
            f"{row['changed_count']} changed  {row['title'] or ''}".rstrip()
        )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check the things that silently break capture. Structured history only —
    the semantic layer is a separate, swappable concern and is not checked here."""
    cwd = Path.cwd()
    root = agentkit_dir(cwd)
    store = db_path(cwd)
    checks: list[tuple[bool, str]] = []

    writable = root.parent.exists() and os.access(root.parent, os.W_OK)
    checks.append((writable, f"shared git dir is writable: {root.parent}"))
    checks.append((store.exists(), f"store exists (else run `agentkit init`): {store}"))

    if store.exists():
        with db.connect(store) as conn:
            names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master")}
        missing = {"sessions", "tool_calls", "changed_files"} - names
        detail = "schema complete" if not missing else f"schema incomplete — missing {missing}"
        checks.append((not missing, detail))

    settings = cwd / ".claude" / "settings.json"
    hooked = settings.exists() and "agentkit capture" in settings.read_text()
    checks.append((hooked, f"SessionEnd hook registered in {settings}"))

    for ok, label in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    failed = [label for ok, label in checks if not ok]
    print(f"{len(checks) - len(failed)}/{len(checks)} checks passed")
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

    doctor = sub.add_parser("doctor", help="check the things that silently break capture")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except NotAGitRepo as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
