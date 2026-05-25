"""FinQA-DSL calculator tool: LLM-invocable arithmetic instead of in-head computation."""

from typing import Any, Union

from pydantic import BaseModel, Field

_OPERATIONS: dict[str, Any] = {
    "add":      lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
    "divide":   lambda a, b: a / b,
    "exp":      lambda a, b: a ** b,
    "greater":  lambda a, b: 1.0 if a > b else 0.0,
}


class Calculate(BaseModel):
    op: str = Field(
        description=f"Arithmetic operation. One of: {', '.join(_OPERATIONS)}."
    )
    arg1: Union[float, str] = Field(
        description="First operand — a literal number or a prior-step back-reference like '#0'."
    )
    arg2: Union[float, str] = Field(
        description="Second operand — a literal number or a prior-step back-reference like '#0'."
    )


def execute(step: Calculate, memory: dict[str, float]) -> float:
    """Resolve operands (including #N back-refs) and apply the operation."""

    def _resolve(arg: float | str) -> float:
        if isinstance(arg, str):
            if arg.startswith("#"):
                if arg not in memory:
                    raise KeyError(f"Back-reference {arg!r} not found. Available: {list(memory)}")
                return memory[arg]
            # Model sent the number as a JSON string (e.g. "206588.0") — parse it.
            return float(arg)
        return float(arg)

    fn = _OPERATIONS.get(step.op)
    if fn is None:
        raise ValueError(f"Unknown op {step.op!r}. Allowed: {list(_OPERATIONS)}")
    return fn(_resolve(step.arg1), _resolve(step.arg2))


def to_anthropic_tool() -> dict[str, Any]:
    raw = Calculate.model_json_schema()
    raw.pop("title", None)
    raw.pop("$defs", None)
    for prop in raw.get("properties", {}).values():
        prop.pop("title", None)
    raw["additionalProperties"] = False
    return {
        "name": "calculate",
        "description": (
            "Execute one arithmetic step and return the numeric result. "
            "Prior results are available as '#0', '#1', etc. for back-references in subsequent calls."
        ),
        "input_schema": raw,
    }
