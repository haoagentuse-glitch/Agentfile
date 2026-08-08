"""Parse an agent transcript into records.

Only the Claude Code JSONL format is supported. Its shape is an external contract
we do not control, so it is pinned by tests against a fixture.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Session:
    session_id: str
    agent: str
    model: str | None
    branch: str | None
    cwd: str | None
    title: str | None
    started_at: str | None
    ended_at: str | None


@dataclass(frozen=True)
class Message:
    role: str
    text: str
    timestamp: str | None


@dataclass(frozen=True)
class ToolCall:
    tool: str
    target: str | None
    timestamp: str | None


@dataclass(frozen=True)
class ParsedTranscript:
    session: Session
    messages: list[Message]
    tool_calls: list[ToolCall]
    changed_files: list[str]


# Tools whose use means the file was modified. Reading a file is not a change.
WRITING_TOOLS = frozenset({"Write", "Edit", "NotebookEdit"})


def _records(path: Path):
    """Yield the JSON objects in a JSONL transcript, skipping unparseable lines."""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def _tool_uses(message: dict):
    """Yield the tool_use blocks of a message, in order."""
    content = message.get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            yield block


def _spoken_text(message: dict) -> str:
    """What was actually said, joined.

    Only `text` blocks count. `thinking` is reasoning, `tool_result` is machine
    output, and both together are most of a transcript's bulk — indexing them
    would duplicate the archive rather than give a way into it.
    """
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n".join(p for p in parts if p).strip()


def parse_transcript(path: Path) -> ParsedTranscript:
    session_id = model = branch = cwd = title = started_at = ended_at = None
    messages: list[Message] = []
    tool_calls: list[ToolCall] = []
    changed_files: list[str] = []

    for record in _records(Path(path)):
        session_id = session_id or record.get("sessionId")
        title = record.get("aiTitle") or title

        timestamp = record.get("timestamp")
        if timestamp:
            started_at = started_at or timestamp
            ended_at = timestamp

        message = record.get("message")
        if isinstance(message, dict):
            branch = record.get("gitBranch") or branch
            cwd = record.get("cwd") or cwd
            model = message.get("model") or model

            text = _spoken_text(message)
            if text:
                messages.append(
                    Message(role=message.get("role", "?"), text=text, timestamp=timestamp)
                )

            for block in _tool_uses(message):
                tool = block.get("name") or "?"
                target = (block.get("input") or {}).get("file_path")
                tool_calls.append(ToolCall(tool=tool, target=target, timestamp=timestamp))
                if tool in WRITING_TOOLS and target and target not in changed_files:
                    changed_files.append(target)

    return ParsedTranscript(
        messages=messages,
        tool_calls=tool_calls,
        changed_files=changed_files,
        session=Session(
            session_id=session_id,
            agent="claude",
            model=model,
            branch=branch,
            cwd=cwd,
            title=title,
            started_at=started_at,
            ended_at=ended_at,
        ),
    )
