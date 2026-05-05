"""Anthropic wire format: message encoding, response decoding, transcript rendering."""

from typing import Any

from pydantic import BaseModel

from src.domain.conversation import Turn

_TOOL_NAME = "submit_answer"
_TOOL_RESULT_ACK = "recorded"


class AnthropicCallResult(BaseModel):
    tool_use_id: str
    tool_input: dict[str, Any]
    tokens_in: int
    tokens_out: int


# ---------- request side -------------------------------------------------


def to_messages(turns: list[Turn], next_question: str) -> list[dict[str, Any]]:
    """Build the Anthropic `messages` list from completed turns plus the next question."""
    if not turns:
        return [{"role": "user", "content": next_question}]

    messages: list[dict[str, Any]] = [{"role": "user", "content": turns[0].question}]
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
    """Parse a raw Anthropic response; raise if no tool_use block with an id is present."""
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
    """Return `{name, input}` for the first tool_use block, or None."""
    for block in raw_response.get("content", []) or []:
        if block.get("type") == "tool_use":
            return {"name": block.get("name"), "input": block.get("input")}
    return None


# ---------- transcript rendering ----------------------------------------


def render_messages_md(messages: list[dict[str, Any]]) -> str:
    """Render a messages list as readable markdown for transcripts.md."""
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
