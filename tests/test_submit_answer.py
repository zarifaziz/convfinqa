"""Snapshot of the JSON Schema we hand to Anthropic for submit_answer."""

from src.tools.submit_answer import SubmitAnswer, to_anthropic_tool


def test_to_anthropic_tool_emits_expected_shape() -> None:
    tool = to_anthropic_tool(SubmitAnswer)

    assert tool == {
        "name": "submit_answer",
        "description": (
            "Submit the final answer after all `calculate` calls are complete. "
            "Pass the exact numeric result from your last calculation."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["reasoning", "answer", "unit"],
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Step-by-step reasoning for the answer.",
                },
                "answer": {
                    "type": "string",
                    "description": (
                        "Final answer as a string. Use the exact numeric result from your last `calculate` call "
                        "(e.g. '25587.0', '0.14136'); booleans as 'yes' or 'no'."
                    ),
                },
                "unit": {
                    "type": "string",
                    "enum": ["raw", "percent", "ratio", "none"],
                    "description": (
                        "Unit hint for the answer. 'raw' for absolute numbers, "
                        "'percent' for percentages (answer expressed as e.g. '14.1' meaning 14.1%), "
                        "'ratio' for unitless fractions, 'none' for yes/no."
                    ),
                },
            },
        },
    }
