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

-- Only what was actually said. Reasoning and tool output stay in the archived
-- transcript; copying them here would duplicate the archive, not index it.
-- Search is substring-based on purpose: FTS5's tokenisers miss two-character
-- Chinese queries, which are the common case.
CREATE TABLE messages (
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    seq        INTEGER NOT NULL,
    role       TEXT NOT NULL,
    text       TEXT NOT NULL,
    timestamp  TEXT,
    PRIMARY KEY (session_id, seq)
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


def upsert_session(
    conn: sqlite3.Connection, session: dict, messages, tool_calls, changed_files
) -> None:
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
    conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
    conn.execute("DELETE FROM tool_calls WHERE session_id = ?", (sid,))
    conn.execute("DELETE FROM changed_files WHERE session_id = ?", (sid,))
    conn.executemany(
        "INSERT INTO messages (session_id, seq, role, text, timestamp) VALUES (?,?,?,?,?)",
        [(sid, i, m.role, m.text, m.timestamp) for i, m in enumerate(messages)],
    )
    conn.executemany(
        "INSERT INTO tool_calls (session_id, seq, tool, target, timestamp) VALUES (?,?,?,?,?)",
        [(sid, i, c.tool, c.target, c.timestamp) for i, c in enumerate(tool_calls)],
    )
    conn.executemany(
        "INSERT INTO changed_files (session_id, path) VALUES (?,?)",
        [(sid, p) for p in changed_files],
    )


def search_messages(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[sqlite3.Row]:
    """Substring search over what was said, newest first."""
    return conn.execute(
        """
        SELECT m.session_id, m.role, m.text, m.timestamp, s.title
        FROM messages m JOIN sessions s ON s.session_id = m.session_id
        WHERE m.text LIKE '%' || ? || '%'
        ORDER BY m.timestamp DESC
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()


def all_sessions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM sessions ORDER BY started_at").fetchall()


def messages_of(conn: sqlite3.Connection, session_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT role, text, timestamp FROM messages WHERE session_id = ? ORDER BY seq",
        (session_id,),
    ).fetchall()


def changed_files_of(conn: sqlite3.Connection, session_id: str) -> list[str]:
    return [
        r["path"]
        for r in conn.execute(
            "SELECT path FROM changed_files WHERE session_id = ? ORDER BY path", (session_id,)
        )
    ]


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
