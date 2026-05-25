"""Anthropic SDK adapter: agentic loop that drives calculate → submit_answer."""

from typing import Any

from anthropic import Anthropic
from pydantic import BaseModel

from src.domain.conversation import Turn
from src.services.llm_client import LLMCallResult
from src.settings import AnthropicSettings
from src.tools.calculator import Calculate
from src.tools.calculator import execute as calc_execute
from src.tools.calculator import to_anthropic_tool as calc_tool
from src.tools.submit_answer import to_anthropic_tool

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
        """Agentic loop: handle any number of `calculate` calls, stop at `submit_answer`."""
        submit_tool = to_anthropic_tool(tool_model)
        tools = [calc_tool(), submit_tool]

        loop_messages = list(messages)
        assistant_exchange: list[dict[str, Any]] = []
        memory: dict[str, float] = {}
        step_idx = 0
        tokens_in_total = 0
        tokens_out_total = 0
        last_raw_response: dict[str, Any] = {}

        while True:
            kwargs: dict[str, Any] = {
                "model": self._model_name,
                "max_tokens": self._MAX_TOKENS,
                "system": system,
                "messages": loop_messages,
                "tools": tools,
                "tool_choice": {"type": "auto"},
            }
            if self._thinking_enabled:
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": self._thinking_budget,
                }
                kwargs["max_tokens"] = self._MAX_TOKENS + self._thinking_budget

            response = self._client.messages.create(**kwargs)
            tokens_in_total += response.usage.input_tokens
            tokens_out_total += response.usage.output_tokens
            last_raw_response = response.model_dump()

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                raise RuntimeError(
                    f"No tool_use in response (stop_reason={response.stop_reason!r}): "
                    f"{response.model_dump()}"
                )

            # Build the assistant content block for this response (preserving thinking blocks)
            assistant_content: list[dict[str, Any]] = []
            for block in response.content:
                if block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                elif block.type == "text" and block.text:
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "thinking":
                    assistant_content.append({
                        "type": "thinking",
                        "thinking": block.thinking,
                        "signature": getattr(block, "signature", ""),
                    })

            assistant_msg: dict[str, Any] = {"role": "assistant", "content": assistant_content}
            loop_messages.append(assistant_msg)
            assistant_exchange.append(assistant_msg)

            # Process each tool call in this response
            tool_results: list[dict[str, Any]] = []
            submit_input: dict[str, Any] | None = None
            submit_id: str | None = None

            for block in tool_uses:
                if block.name == "calculate":
                    step = Calculate.model_validate(block.input)
                    result = calc_execute(step, memory)
                    ref = f"#{step_idx}"
                    memory[ref] = result
                    step_idx += 1
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"{result} (stored as {ref})",
                    })
                elif block.name == submit_tool["name"]:
                    submit_input = block.input
                    submit_id = block.id
                else:
                    raise RuntimeError(f"Unexpected tool call: {block.name!r}")

            if submit_input is not None:
                # Done — return without adding a tool_result for submit_answer;
                # the caller's to_messages() adds the ack when replaying history.
                return LLMCallResult(
                    parsed=tool_model.model_validate(submit_input),
                    tool_use_id=submit_id,
                    raw_response=last_raw_response,
                    tokens_in=tokens_in_total,
                    tokens_out=tokens_out_total,
                    assistant_exchange=assistant_exchange,
                )

            # Feed calculator results back and continue
            if not tool_results:
                raise RuntimeError("Loop iteration had no calculate results and no submit_answer")
            user_msg: dict[str, Any] = {"role": "user", "content": tool_results}
            loop_messages.append(user_msg)
            assistant_exchange.append(user_msg)


def to_messages(turns: list[Turn], next_question: str) -> list[dict[str, Any]]:
    """Build the Anthropic `messages` list from completed turns plus the next question."""
    if not turns:
        return [{"role": "user", "content": next_question}]

    messages: list[dict[str, Any]] = [{"role": "user", "content": turns[0].question}]
    for i, turn in enumerate(turns):
        # Replay the full agentic exchange (calculator calls + submit_answer tool_use)
        messages.extend(turn.assistant_exchange)
        # Ack the submit_answer and carry the next question
        following_question = turns[i + 1].question if i + 1 < len(turns) else next_question
        messages.append({
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": turn.tool_use_id, "content": _TOOL_RESULT_ACK},
                {"type": "text", "text": following_question},
            ],
        })
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
                name = block.get("name")
                if name == "calculate":
                    lines.append(
                        f"**[{role} tool_use {block.get('id')}]** calculate "
                        f"op=`{input_dict.get('op')}` "
                        f"arg1=`{input_dict.get('arg1')}` arg2=`{input_dict.get('arg2')}`"
                    )
                else:
                    lines.append(
                        f"**[{role} tool_use {block.get('id')}]** {name} "
                        f"answer=`{input_dict.get('answer')}` unit=`{input_dict.get('unit')}`"
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
