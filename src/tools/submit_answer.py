"""SubmitAnswer tool schema — submit the final answer once all calculate calls are done."""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field


class SubmitAnswer(BaseModel):
    reasoning: str = Field(description="Step-by-step reasoning for the answer.")
    answer: str = Field(
        description=(
            "Final answer as a string. Use the exact numeric result from your last `calculate` call "
            "(e.g. '25587.0', '0.14136'); booleans as 'yes' or 'no'."
        )
    )
    unit: Literal["raw", "percent", "ratio", "none"] = Field(
        description=(
            "Unit hint for the answer. 'raw' for absolute numbers, "
            "'percent' for percentages (answer expressed as e.g. '14.1' meaning 14.1%), "
            "'ratio' for unitless fractions, 'none' for yes/no."
        )
    )


_TOOL_DESCRIPTIONS: dict[type[BaseModel], str] = {
    SubmitAnswer: (
        "Submit the final answer after all `calculate` calls are complete. "
        "Pass the exact numeric result from your last calculation."
    ),
}


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _strip_pydantic_metadata(schema: dict[str, Any]) -> dict[str, Any]:
    schema.pop("title", None)
    schema.pop("$defs", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    return schema


def to_anthropic_tool(model: type[BaseModel]) -> dict[str, Any]:
    """Convert a Pydantic model into an Anthropic tool dict."""
    raw = model.model_json_schema()
    schema = _strip_pydantic_metadata(raw)
    schema["additionalProperties"] = False
    return {
        "name": _camel_to_snake(model.__name__),
        "description": _TOOL_DESCRIPTIONS[model],
        "input_schema": schema,
    }
