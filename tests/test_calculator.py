"""Unit tests for the FinQA-DSL calculator tool."""

import pytest

from src.tools.calculator import Calculate, execute, to_anthropic_tool


def _step(op: str, arg1: float | str, arg2: float | str) -> Calculate:
    return Calculate(op=op, arg1=arg1, arg2=arg2)


# --- Basic operations ---

def test_add() -> None:
    assert execute(_step("add", 206588, 181001), {}) == pytest.approx(387589.0)


def test_subtract() -> None:
    assert execute(_step("subtract", 206588, 181001), {}) == pytest.approx(25587.0)


def test_multiply() -> None:
    assert execute(_step("multiply", 3, 4), {}) == pytest.approx(12.0)


def test_divide() -> None:
    assert execute(_step("divide", 25587, 181001), {}) == pytest.approx(0.14136, rel=1e-3)


def test_exp() -> None:
    assert execute(_step("exp", 2, 10), {}) == pytest.approx(1024.0)


def test_greater_true() -> None:
    assert execute(_step("greater", 206588, 181001), {}) == 1.0


def test_greater_false() -> None:
    assert execute(_step("greater", 100, 200), {}) == 0.0


# --- Back-references ---

def test_back_reference_single_step() -> None:
    memory = {"#0": 25587.0}
    result = execute(_step("divide", "#0", 181001), memory)
    assert result == pytest.approx(0.14136, rel=1e-3)


def test_multi_step_chained() -> None:
    """Simulate: subtract(206588, 181001) → #0; divide(#0, 181001) → answer."""
    memory: dict[str, float] = {}
    step0 = _step("subtract", 206588, 181001)
    r0 = execute(step0, memory)
    memory["#0"] = r0

    step1 = _step("divide", "#0", 181001)
    r1 = execute(step1, memory)

    assert r0 == pytest.approx(25587.0)
    assert r1 == pytest.approx(0.14136, rel=1e-3)


def test_back_reference_both_args() -> None:
    memory = {"#0": 10.0, "#1": 2.0}
    assert execute(_step("divide", "#0", "#1"), memory) == pytest.approx(5.0)


# --- Error cases ---

def test_unknown_op_raises() -> None:
    with pytest.raises(ValueError, match="Unknown op"):
        execute(_step("exfiltrate", 1, 2), {})


def test_missing_back_ref_raises() -> None:
    with pytest.raises(KeyError, match="#99"):
        execute(_step("add", "#99", 1), {})


def test_divide_by_zero_raises() -> None:
    with pytest.raises(ZeroDivisionError):
        execute(_step("divide", 1, 0), {})


# --- Anthropic tool schema ---

def test_to_anthropic_tool_shape() -> None:
    tool = to_anthropic_tool()

    assert tool == {
        "name": "calculate",
        "description": (
            "Execute one arithmetic step and return the numeric result. "
            "Prior results are available as '#0', '#1', etc. for back-references in subsequent calls."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["op", "arg1", "arg2"],
            "properties": {
                "op": {
                    "type": "string",
                    "description": "Arithmetic operation. One of: add, subtract, multiply, divide, exp, greater.",
                },
                "arg1": {
                    "anyOf": [{"type": "number"}, {"type": "string"}],
                    "description": "First operand — a literal number or a prior-step back-reference like '#0'.",
                },
                "arg2": {
                    "anyOf": [{"type": "number"}, {"type": "string"}],
                    "description": "Second operand — a literal number or a prior-step back-reference like '#0'.",
                },
            },
        },
    }
