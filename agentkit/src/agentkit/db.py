"""The SQLite store.

This schema is a persisted format — a hard-to-reverse decision. Change it deliberately,
and record an ADR when the shape changes.
"""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE sessions (
    session_id      TEXT PRIMARY KEY,
    agent           TEXT NOT NULL,
    model           TEXT,
    title           TEXT,
    branch          TEXT,
    worktree        TEXT,
    cwd             TEXT,
    started_at      TEXT,
    ended_at        TEXT,
    transcript_path TEXT,
    commit_sha      TEXT
);

CREATE TABLE tool_calls (
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    seq        INTEGER NOT NULL,
    tool       TEXT NOT NULL,
    target     TEXT,
    timestamp  TEXT,
    PRIMARY KEY (session_id, seq)
);

CREATE TABLE changed_files (
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    path       TEXT NOT NULL,
    PRIMARY KEY (session_id, path)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create(path: Path) -> None:
    """Create the store. Caller guarantees it does not already exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)


def upsert_session(conn: sqlite3.Connection, session: dict, tool_calls, changed_files) -> None:
    """Write one session and its children, replacing any earlier capture of it.

    SessionEnd can fire more than once for a session (resume, clear), so this is
    a replace rather than an append.
    """
    conn.execute(
        """
        INSERT OR REPLACE INTO sessions
            (session_id, agent, model, title, branch, worktree, cwd,
             started_at, ended_at, transcript_path, commit_sha)
        VALUES
            (:session_id, :agent, :model, :title, :branch, :worktree, :cwd,
             :started_at, :ended_at, :transcript_path, :commit_sha)
        """,
        session,
    )
    sid = session["session_id"]
    conn.execute("DELETE FROM tool_calls WHERE session_id = ?", (sid,))
    conn.execute("DELETE FROM changed_files WHERE session_id = ?", (sid,))
    conn.executemany(
        "INSERT INTO tool_calls (session_id, seq, tool, target, timestamp) VALUES (?,?,?,?,?)",
        [(sid, i, c.tool, c.target, c.timestamp) for i, c in enumerate(tool_calls)],
    )
    conn.executemany(
        "INSERT INTO changed_files (session_id, path) VALUES (?,?)",
        [(sid, p) for p in changed_files],
    )


def recent_sessions(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT s.*, (SELECT COUNT(*) FROM changed_files c WHERE c.session_id = s.session_id)
                    AS changed_count
        FROM sessions s
        ORDER BY COALESCE(s.ended_at, s.started_at) DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
