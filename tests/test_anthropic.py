"""Snapshot test for `to_messages` — pins the Anthropic wire shape."""

from src.domain import PredictedAnswer
from src.domain.conversation import Turn
from src.services.anthropic import to_messages

TOOL_NAME = "submit_answer"
TOOL_RESULT_ACK = "recorded"


def _predicted(answer: str) -> PredictedAnswer:
    return PredictedAnswer(
        reasoning="r",
        calculation="100",
        sign_convention="signed",
        answer=answer,
        unit="raw",
    )


def _assistant_tool_use(tool_use_id: str, predicted: PredictedAnswer) -> dict:
    return {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": tool_use_id,
                "name": TOOL_NAME,
                "input": predicted.model_dump(),
            }
        ],
    }


def _user_tool_result_then_text(tool_use_id: str, next_q: str) -> dict:
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": TOOL_RESULT_ACK,
            },
            {"type": "text", "text": next_q},
        ],
    }


def test_to_messages_three_prior_turns_full_alternation() -> None:
    p0, p1, p2 = _predicted("a"), _predicted("b"), _predicted("c")
    turns = [
        Turn(question="Q0", tool_use_id="tool_0", predicted=p0),
        Turn(question="Q1", tool_use_id="tool_1", predicted=p1),
        Turn(question="Q2", tool_use_id="tool_2", predicted=p2),
    ]
    assert to_messages(turns, "Q3") == [
        {"role": "user", "content": "Q0"},
        _assistant_tool_use("tool_0", p0),
        _user_tool_result_then_text("tool_0", "Q1"),
        _assistant_tool_use("tool_1", p1),
        _user_tool_result_then_text("tool_1", "Q2"),
        _assistant_tool_use("tool_2", p2),
        _user_tool_result_then_text("tool_2", "Q3"),
    ]
