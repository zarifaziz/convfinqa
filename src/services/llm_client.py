"""LLM-call abstraction.

`LLMClient` is the structural Protocol services depend on; `AnthropicClient`
implements it against the Anthropic SDK with forced `tool_choice`. Tests
substitute `FakeLLMClient` (in `tests/fakes/`) — no API key needed.
"""

from typing import Any, Protocol, runtime_checkable

from anthropic import Anthropic
from pydantic import BaseModel

from src.settings import AnthropicSettings
from src.tools.submit_answer import to_anthropic_tool


@runtime_checkable
class LLMClient(Protocol):
    def predict_with_tool(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tool_model: type[BaseModel],
    ) -> tuple[BaseModel, dict[str, Any]]: ...


class AnthropicClient:
    """Thin Anthropic SDK wrapper with forced tool-choice. Implements `LLMClient`.

    Forced `tool_choice` collapses output parsing to schema validation: the
    response either carries a tool_use block matching the requested model or
    raises a hard error worth seeing.
    """

    # Output cap
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
    ) -> tuple[BaseModel, dict[str, Any]]:
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
            # tool_choice "tool" is rejected with thinking; "any" still forces
            # a tool call when only one tool is registered.
            kwargs["tool_choice"] = {"type": "any"}
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

        parsed = tool_model.model_validate(tool_use.input)
        return parsed, response.model_dump()
