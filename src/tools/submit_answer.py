"""The single tool the model is forced to call: `submit_answer`.

The pydantic model defines the wire shape; `to_anthropic_tool` converts it
into the dict Anthropic expects. Forcing tool-use eliminates regex over
free-form prose — the response either parses or surfaces a hard error.
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field


class SubmitAnswer(BaseModel):
    reasoning: str = Field(description="Step-by-step reasoning for the answer.")
    calculation: str = Field(
        description="Arithmetic expression that produced the answer, e.g. '206588 - 181001'."
    )
    answer: str = Field(
        description=(
            "Final answer as a string. Numbers as plain digits "
            "(e.g. '25587', '0.141', '14.1'); booleans as 'yes' or 'no'."
        )
    )
    unit: Literal["raw", "percent", "ratio", "none"] = Field(
        description=(
            "Unit hint for the answer. 'raw' for absolute numbers, "
            "'percent' for percentages (e.g. '14.1' meaning 14.1%), "
            "'ratio' for unitless fractions, 'none' if not applicable."
        )
    )


_TOOL_DESCRIPTIONS: dict[type[BaseModel], str] = {
    SubmitAnswer: (
        "Submit the final answer to the user's question, with the reasoning, "
        "the arithmetic expression you used, the answer string, and a unit hint."
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
    """Convert a pydantic model into the Anthropic tool dict shape.

    Pydantic emits richer JSON Schema than Anthropic needs (`title`, `$defs`).
    We strip those, then pin `additionalProperties: False` so the model can't
    invent extra fields — anything outside the schema becomes a hard error
    rather than silently dropped data.
    """
    raw = model.model_json_schema()
    schema = _strip_pydantic_metadata(raw)
    schema["additionalProperties"] = False

    return {
        "name": _camel_to_snake(model.__name__),
        "description": _TOOL_DESCRIPTIONS[model],
        "input_schema": schema,
    }
