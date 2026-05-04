"""Snapshot tests pinning the JSON Schema we hand to Anthropic.

The tool schema is the contract between us and the model. Drift here would
silently change what the model is allowed to emit, so we snapshot the full
shape and assert on it as a single dict.
"""

from src.tools.submit_answer import SubmitAnswer, to_anthropic_tool


def test_submit_answer_pydantic_round_trip() -> None:
    instance = SubmitAnswer(
        reasoning="206588 - 181001 = 25587",
        calculation="206588 - 181001",
        sign_convention="signed",
        answer="25587",
        unit="raw",
    )
    assert instance.model_dump() == {
        "reasoning": "206588 - 181001 = 25587",
        "calculation": "206588 - 181001",
        "sign_convention": "signed",
        "answer": "25587",
        "unit": "raw",
    }


def test_submit_answer_unit_enum_rejects_unknown_values() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SubmitAnswer(
            reasoning="x",
            calculation="x",
            sign_convention="n/a",
            answer="x",
            unit="dollars",  # not in {raw, percent, ratio, none}
        )


def test_submit_answer_sign_convention_coerces_unknown_to_signed() -> None:
    # Defensive: if the model emits a value outside the enum (common confusion
    # with `unit`, e.g. emitting 'ratio'), validation must not crash the eval.
    # Coerced to 'signed' — the safe default for arithmetic-result questions.
    instance = SubmitAnswer.model_validate(
        {
            "reasoning": "x",
            "calculation": "x",
            "sign_convention": "ratio",  # not in {magnitude, signed, n/a}
            "answer": "x",
            "unit": "raw",
        }
    )
    assert instance.sign_convention == "signed"


def test_to_anthropic_tool_emits_expected_shape() -> None:
    tool = to_anthropic_tool(SubmitAnswer)

    assert tool == {
        "name": "submit_answer",
        "description": (
            "Submit the final answer to the user's question, with the reasoning, "
            "the arithmetic expression you used, the answer string, and a unit hint."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "reasoning",
                "calculation",
                "sign_convention",
                "answer",
                "unit",
            ],
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Step-by-step reasoning for the answer.",
                },
                "calculation": {
                    "type": "string",
                    "description": "Arithmetic expression that produced the answer, e.g. '206588 - 181001'.",
                },
                "sign_convention": {
                    "type": "string",
                    "enum": ["magnitude", "signed", "n/a"],
                    "description": (
                        "Does the question want a signed value (direction matters) or a magnitude (size only)? "
                        "'signed' for arithmetic results — change, difference, X minus Y, net values. "
                        "'magnitude' when the question names an inherently non-negative quantity (rate, yield, "
                        "loss, charge) and the table's negative sign is a display convention. "
                        "'n/a' only for yes/no questions."
                    ),
                },
                "answer": {
                    "type": "string",
                    "description": (
                        "Final answer as a string. Numbers as plain digits "
                        "(e.g. '25587', '0.141', '14.1'); booleans as 'yes' or 'no'."
                    ),
                },
                "unit": {
                    "type": "string",
                    "enum": ["raw", "percent", "ratio", "none"],
                    "description": (
                        "Unit hint for the answer. 'raw' for absolute numbers, "
                        "'percent' for percentages (e.g. '14.1' meaning 14.1%), "
                        "'ratio' for unitless fractions, 'none' if not applicable."
                    ),
                },
            },
        },
    }


def test_to_anthropic_tool_strips_pydantic_metadata() -> None:
    """`title` and `$defs` from pydantic's JSON Schema should not reach Anthropic."""
    tool = to_anthropic_tool(SubmitAnswer)
    assert "title" not in tool["input_schema"]
    assert "$defs" not in tool["input_schema"]
    for prop in tool["input_schema"]["properties"].values():
        assert "title" not in prop
