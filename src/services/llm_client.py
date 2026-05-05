"""Provider-agnostic LLM call abstraction."""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class LLMCallResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    parsed: BaseModel
    tool_use_id: str
    raw_response: dict[str, Any]
    tokens_in: int
    tokens_out: int


@runtime_checkable
class LLMClient(Protocol):
    def predict_with_tool(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tool_model: type[BaseModel],
    ) -> LLMCallResult: ...
