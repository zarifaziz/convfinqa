"""Per-call transcript writers.

Two sibling files per run:
  - `transcripts.jsonl` — machine-readable, one JSON object per line, full
    record (incl. raw_response) for `jq` queries and replay tooling.
  - `transcripts.md` — human-readable, multi-line markdown sections per
    call, real newlines preserved. Skips `raw_response` to keep it skimmable.

The orchestrator calls both; `Answerer` stays a pure transformer.
"""

import json
from pathlib import Path
from typing import Any


def write_transcript(path: Path, line: dict[str, Any]) -> None:
    """Append one JSON object as a single line to `path`. File is created if missing."""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False, default=str))
        fh.write("\n")


def write_transcript_md(path: Path, line: dict[str, Any]) -> None:
    """Append a markdown section for one call. Real newlines, no raw_response."""
    parsed = line.get("parsed") or {}
    tool_call = line.get("tool_call") or {}
    messages = line.get("messages") or []
    user_message = next((m["content"] for m in messages if m.get("role") == "user"), "")

    section = (
        f"# {line.get('record_id')} (turn {line.get('turn_idx')})\n\n"
        f"**correct:** {line.get('correct')} &nbsp;&nbsp; "
        f"**latency:** {line.get('latency_ms')} ms &nbsp;&nbsp; "
        f"**gold:** `{line.get('gold')!r}`\n\n"
        f"## Question\n\n"
        f"{line.get('question')}\n\n"
        f"## User message\n\n"
        f"{user_message}\n\n"
        f"## System prompt\n\n"
        f"```\n{line.get('system_prompt', '')}\n```\n\n"
        f"## Tool call ({tool_call.get('name')!r})\n\n"
        f"- **reasoning:** {parsed.get('reasoning')}\n"
        f"- **calculation:** `{parsed.get('calculation')}`\n"
        f"- **answer:** `{parsed.get('answer')}`\n"
        f"- **unit:** `{parsed.get('unit')}`\n\n"
        f"---\n\n"
    )
    with path.open("a", encoding="utf-8") as fh:
        fh.write(section)
