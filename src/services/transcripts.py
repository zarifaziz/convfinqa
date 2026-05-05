"""Append per-call transcripts to JSONL and markdown files."""

import json
from pathlib import Path
from typing import Any

from src.services import anthropic


def write_transcript(path: Path, line: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False, default=str))
        fh.write("\n")


def write_transcript_md(path: Path, line: dict[str, Any]) -> None:
    parsed = line.get("parsed") or {}
    tool_call = line.get("tool_call") or {}
    messages = line.get("messages") or []

    section = f"""\
# {line.get("record_id")} (turn {line.get("turn_idx")})

**correct:** {line.get("correct")} &nbsp;&nbsp; **latency:** {line.get("latency_ms")} ms &nbsp;&nbsp; **gold:** `{line.get("gold")!r}` &nbsp;&nbsp; **question:** {line.get("question")}

## System prompt

```
{line.get("system_prompt", "")}
```

## Messages (prior turns + current question)

{anthropic.render_messages_md(messages)}
## Response — tool call ({tool_call.get("name")!r})

- **reasoning:** {parsed.get("reasoning")}
- **calculation:** `{parsed.get("calculation")}`
- **answer:** `{parsed.get("answer")}`
- **unit:** `{parsed.get("unit")}`

---

"""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(section)
