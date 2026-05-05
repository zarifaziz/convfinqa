"""Anthropic SDK adapter and wire format helpers."""

from typing import Any

from anthropic import Anthropic
from pydantic import BaseModel

from src.domain.conversation import Turn
from src.services.llm_client import LLMCallResult
from src.settings import AnthropicSettings
from src.tools.submit_answer import to_anthropic_tool

_TOOL_NAME = "submit_answer"
_TOOL_RESULT_ACK = "recorded"


class AnthropicClient:
    _MAX_TOKENS = 4096

    def __init__(self, settings: AnthropicSettings) -> None:
        # `max_retries=4`: SDK default is 2; at concurrency=15 we sit around
        # half the input-TPM cap, so transient 429s on hot windows are
        # expected. Backoff is exponential — worst-case wall hit ~30s, far
        # cheaper than crashing the whole eval.
        self._client = Anthropic(api_key=settings.api_key, max_retries=4)
        self._model_name = settings.model_name
        self._thinking_enabled = settings.thinking_enabled
        self._thinking_budget = settings.thinking_budget_tokens

    def predict_with_tool(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tool_model: type[BaseModel],
    ) -> LLMCallResult:
        tool_dict = to_anthropic_tool(tool_model)

        kwargs: dict[str, Any] = {
            "model": self._model_name,
            "max_tokens": self._MAX_TOKENS,
            "system": system,
            "messages": messages,
            "tools": [tool_dict],
            "tool_choice": {"type": "tool", "name": tool_dict["name"]},
        }
        if self._thinking_enabled:
            # API rejects any forced tool_choice ("tool" or "any") with thinking
            # enabled — only "auto" is allowed. We rely on the single registered
            # tool plus the system-prompt instruction to coerce a tool_use block;
            # if the model returns text instead, the missing-tool_use guard below
            # raises a hard error rather than silently skipping the turn.
            kwargs["tool_choice"] = {"type": "auto"}
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": self._thinking_budget,
            }
            # API requires max_tokens > budget_tokens; add the budget on top.
            kwargs["max_tokens"] = self._MAX_TOKENS + self._thinking_budget

        response = self._client.messages.create(**kwargs)

        tool_use = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_use is None:
            raise RuntimeError(
                f"Forced tool_choice but no tool_use block in response: {response.model_dump()}"
            )
        if not tool_use.input:
            # Almost always: stop_reason='max_tokens' — model truncated mid-JSON.
            raise RuntimeError(
                f"Empty tool_use.input (stop_reason={response.stop_reason!r}, "
                f"output tokens={response.usage.output_tokens}). Likely "
                f"max_tokens cap; bump _MAX_TOKENS or shorten the schema."
            )

        return LLMCallResult(
            parsed=tool_model.model_validate(tool_use.input),
            tool_use_id=tool_use.id,
            raw_response=response.model_dump(),
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
        )


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


def extract_tool_call(raw_response: dict[str, Any]) -> dict[str, Any] | None:
    """Return `{name, input}` for the first tool_use block, or None."""
    for block in raw_response.get("content", []) or []:
        if block.get("type") == "tool_use":
            return {"name": block.get("name"), "input": block.get("input")}
    return None


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
