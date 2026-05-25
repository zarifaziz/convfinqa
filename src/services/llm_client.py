"""Provider-agnostic LLM call abstraction."""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class LLMCallResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    parsed: BaseModel
    tool_use_id: str
    raw_response: dict[str, Any]
    tokens_in: int
    tokens_out: int
    # All messages produced by the agentic loop for this turn (calculator calls +
    # submit_answer block). Used to replay conversations in subsequent turns.
    assistant_exchange: list[dict[str, Any]] = Field(default_factory=list)


@runtime_checkable
class LLMClient(Protocol):
    def predict_with_tool(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tool_model: type[BaseModel],
    ) -> LLMCallResult: ...
