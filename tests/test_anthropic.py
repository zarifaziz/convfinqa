"""Snapshot test for `to_messages` — pins the Anthropic wire shape."""

from src.domain import PredictedAnswer
from src.domain.conversation import Turn
from src.services.anthropic import to_messages

TOOL_NAME = "submit_answer"
TOOL_RESULT_ACK = "recorded"


def _predicted(answer: str) -> PredictedAnswer:
    return PredictedAnswer(reasoning="r", answer=answer, unit="raw")


def _submit_answer_block(tool_use_id: str, predicted: PredictedAnswer) -> dict:
    return {
        "type": "tool_use",
        "id": tool_use_id,
        "name": TOOL_NAME,
        "input": predicted.model_dump(),
    }


def _assistant_exchange(tool_use_id: str, predicted: PredictedAnswer) -> list[dict]:
    """The assistant_exchange stored on a turn that had no calculator calls."""
    return [
        {
            "role": "assistant",
            "content": [_submit_answer_block(tool_use_id, predicted)],
        }
    ]


def _user_tool_result_then_text(tool_use_id: str, next_q: str) -> dict:
    return {
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": tool_use_id, "content": TOOL_RESULT_ACK},
            {"type": "text", "text": next_q},
        ],
    }


def _turn(question: str, tool_use_id: str, predicted: PredictedAnswer) -> Turn:
    return Turn(
        question=question,
        tool_use_id=tool_use_id,
        predicted=predicted,
        assistant_exchange=_assistant_exchange(tool_use_id, predicted),
    )


def test_to_messages_three_prior_turns_full_alternation() -> None:
    p0, p1, p2 = _predicted("a"), _predicted("b"), _predicted("c")
    turns = [
        _turn("Q0", "tool_0", p0),
        _turn("Q1", "tool_1", p1),
        _turn("Q2", "tool_2", p2),
    ]
    assert to_messages(turns, "Q3") == [
        {"role": "user", "content": "Q0"},
        {"role": "assistant", "content": [_submit_answer_block("tool_0", p0)]},
        _user_tool_result_then_text("tool_0", "Q1"),
        {"role": "assistant", "content": [_submit_answer_block("tool_1", p1)]},
        _user_tool_result_then_text("tool_1", "Q2"),
        {"role": "assistant", "content": [_submit_answer_block("tool_2", p2)]},
        _user_tool_result_then_text("tool_2", "Q3"),
    ]


def test_to_messages_with_calculator_steps_in_exchange() -> None:
    """Verify that calculator steps in the exchange are replayed verbatim."""
    p0 = _predicted("25587.0")
    calc_tool_id = "calc_0"
    submit_tool_id = "tool_0"
    # A turn where the model called calculate before submit_answer
    exchange = [
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": calc_tool_id,
                    "name": "calculate",
                    "input": {"op": "subtract", "arg1": 206588, "arg2": 181001},
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": calc_tool_id,
                    "content": "25587.0 (stored as #0)",
                }
            ],
        },
        {
            "role": "assistant",
            "content": [_submit_answer_block(submit_tool_id, p0)],
        },
    ]
    turn = Turn(
        question="Q0",
        tool_use_id=submit_tool_id,
        predicted=p0,
        assistant_exchange=exchange,
    )
    messages = to_messages([turn], "Q1")
    assert messages == [
        {"role": "user", "content": "Q0"},
        *exchange,
        _user_tool_result_then_text(submit_tool_id, "Q1"),
    ]
