"""Anthropic adapter — the one module that knows the Anthropic API shape.

Every line that touches the Anthropic block taxonomy (`tool_use`,
`tool_result`, `text`) and field names (`id`, `tool_use_id`, `input`,
`usage.input_tokens`, ...) lives here. Callers stay provider-agnostic
above this seam:

  - `to_messages` builds the API `messages` list from completed turns
    (encoder: structured turns -> request payload).
  - `parse_response` reads a raw response dump into a typed
    `AnthropicCallResult` (decoder: response payload -> structured fields).
  - `extract_tool_call` returns the `tool_use` summary used by transcripts.
  - `render_messages_md` renders a messages list for human-readable transcripts.

Naming is deliberately Anthropic-specific (see `docs/decisions.md`,
"Explicit provider naming over generic abstraction"). Adding a second
provider means adding `<provider>.py` next to this file, not abstracting
this one behind a Protocol.
"""

from typing import Any

from pydantic import BaseModel

from src.domain.conversation import Turn

_TOOL_NAME = "submit_answer"
_TOOL_RESULT_ACK = "recorded"


class AnthropicCallResult(BaseModel):
    """Structured view of one Anthropic response. Pulled from `raw_response`
    by `parse_response` so callers don't dig into nested dicts themselves.
    """

    tool_use_id: str
    tool_input: dict[str, Any]
    tokens_in: int
    tokens_out: int


# ---------- request side -------------------------------------------------


def to_messages(turns: list[Turn], next_question: str) -> list[dict[str, Any]]:
    """Serialize completed `turns` plus a new `next_question` into the
    Anthropic `messages` list shape.

    Rules (any violation -> HTTP 400):
      - User / assistant alternation.
      - Each `tool_use` block followed by a `tool_result` with matching
        `tool_use_id`.
      - The next question rides as a second content block in the same user
        message as the prior turn's `tool_result` (two consecutive user
        messages also 400).
      - The document is NOT in messages — it lives in the system prompt.
    """
    if not turns:
        return [{"role": "user", "content": next_question}]

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": turns[0].question}
    ]
    for i, turn in enumerate(turns):
        messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": turn.tool_use_id,
                        "name": _TOOL_NAME,
                        "input": turn.predicted.model_dump(),
                    }
                ],
            }
        )
        following_question = (
            turns[i + 1].question if i + 1 < len(turns) else next_question
        )
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": turn.tool_use_id,
                        "content": _TOOL_RESULT_ACK,
                    },
                    {"type": "text", "text": following_question},
                ],
            }
        )
    return messages


# ---------- response side ------------------------------------------------


def parse_response(raw_response: dict[str, Any]) -> AnthropicCallResult:
    """Parse a raw Anthropic response into the fields callers actually use.

    Raises if no `tool_use` block with an `id` is present — without that id
    the next turn cannot be replayed (would 400 on the API), so a missing
    id is a hard error worth surfacing immediately.
    """
    tool_use_id: str | None = None
    tool_input: dict[str, Any] = {}
    for block in raw_response.get("content", []) or []:
        if block.get("type") == "tool_use" and block.get("id"):
            tool_use_id = block["id"]
            tool_input = block.get("input") or {}
            break
    if tool_use_id is None:
        raise RuntimeError(
            "no tool_use block with an id in raw response; cannot continue conversation"
        )

    usage = raw_response.get("usage") or {}
    return AnthropicCallResult(
        tool_use_id=tool_use_id,
        tool_input=tool_input,
        tokens_in=int(usage.get("input_tokens", 0) or 0),
        tokens_out=int(usage.get("output_tokens", 0) or 0),
    )


def extract_tool_call(raw_response: dict[str, Any]) -> dict[str, Any] | None:
    """Return `{name, input}` for the first `tool_use` block, or None.

    Used by transcript writers — they want the tool call summary without
    needing the full `AnthropicCallResult` (which would error on a response
    that legitimately has no tool_use, e.g. future free-text responses).
    """
    for block in raw_response.get("content", []) or []:
        if block.get("type") == "tool_use":
            return {"name": block.get("name"), "input": block.get("input")}
    return None


# ---------- transcript rendering ----------------------------------------


def render_messages_md(messages: list[dict[str, Any]]) -> str:
    """Render the messages list as readable markdown for `transcripts.md`.

    Each message is one labelled block. `tool_use` shows the prior-turn
    answer the model emitted; `tool_result` shows the synthetic ack;
    `text` shows the question. Block-type knowledge stays in this file.
    """
    if not messages:
        return "_(none)_\n"

    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content")
        if isinstance(content, str):
            lines.append(f"**[{role}]** {content}")
            continue
        if not isinstance(content, list):
            lines.append(f"**[{role}]** {content!r}")
            continue
        for block in content:
            btype = block.get("type")
            if btype == "tool_use":
                input_dict = block.get("input") or {}
                answer = input_dict.get("answer")
                lines.append(
                    f"**[{role} tool_use {block.get('id')}]** answer=`{answer}` "
                    f"calculation=`{input_dict.get('calculation')}`"
                )
            elif btype == "tool_result":
                lines.append(
                    f"**[{role} tool_result {block.get('tool_use_id')}]** "
                    f"{block.get('content')}"
                )
            elif btype == "text":
                lines.append(f"**[{role} text]** {block.get('text')}")
            else:
                lines.append(f"**[{role} {btype}]** {block!r}")
    return "\n\n".join(lines) + "\n\n"
