"""SubmitAnswer tool schema and Anthropic tool-dict adapter."""

import re
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field, field_validator


class SubmitAnswer(BaseModel):
    reasoning: str = Field(description="Step-by-step reasoning for the answer.")
    calculation: str = Field(
        description="Arithmetic expression that produced the answer, e.g. '206588 - 181001'."
    )
    sign_convention: Literal["magnitude", "signed", "n/a"] = Field(
        description=(
            "Does the question want a signed value (direction matters) or a magnitude (size only)? "
            "'signed' for arithmetic results — change, difference, X minus Y, net values. "
            "'magnitude' when the question names an inherently non-negative quantity (rate, yield, "
            "loss, charge) and the table's negative sign is a display convention. "
            "'n/a' only for yes/no questions."
        )
    )

    @field_validator("sign_convention", mode="before")
    @classmethod
    def _coerce_unknown(cls, v: object) -> object:
        # Coerce out-of-enum values to 'signed' so a single bad turn doesn't crash the eval.
        if isinstance(v, str) and v not in ("magnitude", "signed", "n/a"):
            logger.warning("sign_convention out of enum: {!r} → coerced to 'signed'", v)
            return "signed"
        return v

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
    """Convert a pydantic model into the Anthropic tool dict; strip metadata, lock additionalProperties."""
    raw = model.model_json_schema()
    schema = _strip_pydantic_metadata(raw)
    schema["additionalProperties"] = False

    return {
        "name": _camel_to_snake(model.__name__),
        "description": _TOOL_DESCRIPTIONS[model],
        "input_schema": schema,
    }
