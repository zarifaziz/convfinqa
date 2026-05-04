"""Per-call transcript writers.

Two sibling files per run:
  - `transcripts.jsonl` — machine-readable, one JSON object per line, full
    record (incl. raw_response) for `jq` queries and replay tooling.
  - `transcripts.md` — human-readable, multi-line markdown sections per
    call, real newlines preserved. Skips `raw_response` to keep it skimmable.

Wire-shape rendering of the messages list lives in `anthropic`; this
module is the orchestration of section ordering, not block-type knowledge.
"""

import json
from pathlib import Path
from typing import Any

from src.services import anthropic


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

    # Section order mirrors what the model actually receives on the wire:
    # `system` first, then the `messages` list, then its tool_use response.
    section = f"""\
# {line.get('record_id')} (turn {line.get('turn_idx')})

**correct:** {line.get('correct')} &nbsp;&nbsp; **latency:** {line.get('latency_ms')} ms &nbsp;&nbsp; **gold:** `{line.get('gold')!r}` &nbsp;&nbsp; **question:** {line.get('question')}

## System prompt

```
{line.get('system_prompt', '')}
```

## Messages (prior turns + current question)

{anthropic.render_messages_md(messages)}
## Response — tool call ({tool_call.get('name')!r})

- **reasoning:** {parsed.get('reasoning')}
- **calculation:** `{parsed.get('calculation')}`
- **answer:** `{parsed.get('answer')}`
- **unit:** `{parsed.get('unit')}`

---

"""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(section)
