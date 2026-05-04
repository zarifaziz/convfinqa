"""The single tool the model is forced to call: `submit_answer`.

The pydantic model defines the wire shape; `to_anthropic_tool` converts it
into the dict Anthropic expects. Forcing tool-use eliminates regex over
free-form prose — the response either parses or surfaces a hard error.
"""

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
            "Whether the question wants a magnitude (sign stripped) or a signed value (sign preserved). "
            "This is NOT the unit — for percent or ratio quantities, set `unit='percent'` or `unit='ratio'` "
            "separately; sign_convention is solely about whether the answer carries a sign. "
            "Decide before writing `answer`; the sign of `answer` must match this choice. "
            "Use 'magnitude' for inherently non-negative quantities (discount rates, yields, returns, margins) "
            "and for 'what were the losses / charges / write-downs in <year>?' — the cell's negative sign is the "
            "earnings impact, but the loss IS the magnitude. "
            "Use 'signed' for arithmetic-result and net values where the direction matters: 'change', "
            "'variation', 'difference', 'increase', 'decrease', 'decline', 'drop', 'growth', 'net cash flow', "
            "'net income', 'net loss', 'X less Y', 'X minus Y'. For 'X less Y' / 'X minus Y' / 'difference "
            "between X and Y', compute X − Y in the order named — the result may be negative. For 'decline / "
            "decrease / drop', preserve the sign produced by the arithmetic; do not strip it. "
            "Use 'n/a' ONLY for boolean (yes/no) answers. NEVER assign 'n/a' to a numeric question, even if "
            "the answer is zero or you are uncertain — pick 'magnitude' or 'signed'."
        )
    )

    @field_validator("sign_convention", mode="before")
    @classmethod
    def _coerce_unknown(cls, v: object) -> object:
        # Defensive coercion: if the model emits a value outside the enum
        # (most common: confusion with `unit` and emitting 'ratio'), don't crash
        # the whole eval run — log loudly and fall back to 'signed' (the safe
        # default for arithmetic-result questions, which dominate this dataset).
        if isinstance(v, str) and v not in ("magnitude", "signed", "n/a"):
            logger.warning(
                "sign_convention out of enum: {!r} → coerced to 'signed'", v
            )
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
