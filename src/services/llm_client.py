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

    # Anthropic requires `max_tokens` on every call but it caps output, not
    # input. 1024 comfortably covers a `submit_answer` tool call (reasoning
    # + calculation + answer + unit). Hardcoded so it isn't config surface.
    _MAX_TOKENS = 1024

    def __init__(self, settings: AnthropicSettings) -> None:
        self._client = Anthropic(api_key=settings.api_key)
        self._model_name = settings.model_name

    def predict_with_tool(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tool_model: type[BaseModel],
    ) -> tuple[BaseModel, dict[str, Any]]:
        tool_dict = to_anthropic_tool(tool_model)

        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=self._MAX_TOKENS,
            system=system,
            messages=messages,
            tools=[tool_dict],
            tool_choice={"type": "tool", "name": tool_dict["name"]},
        )

        tool_use = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_use is None:
            raise RuntimeError(
                f"Forced tool_choice but no tool_use block in response: {response.model_dump()}"
            )

        parsed = tool_model.model_validate(tool_use.input)
        return parsed, response.model_dump()
