"""Snapshot tests for the Anthropic wire-format helpers."""

from src.domain import PredictedAnswer
from src.domain.conversation import Turn
from src.services.anthropic import (
    extract_tool_call,
    render_messages_md,
    to_messages,
)

TOOL_NAME = "submit_answer"
TOOL_RESULT_ACK = "recorded"


def _predicted(answer: str = "100", unit: str = "raw") -> PredictedAnswer:
    return PredictedAnswer(
        reasoning="r",
        calculation="100",
        sign_convention="signed",
        answer=answer,
        unit=unit,
    )


def _turn(q: str, tool_use_id: str, predicted: PredictedAnswer) -> Turn:
    return Turn(question=q, tool_use_id=tool_use_id, predicted=predicted)


def _user_text(text: str) -> dict:
    return {"role": "user", "content": text}


def _assistant_tool_use(tool_use_id: str, input_dict: dict) -> dict:
    return {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": tool_use_id,
                "name": TOOL_NAME,
                "input": input_dict,
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


# ---------- to_messages ---------------------------------------------------


def test_to_messages_zero_prior_turns_emits_single_user_message() -> None:
    assert to_messages([], "Q0") == [_user_text("Q0")]


def test_to_messages_one_prior_turn_pairs_tool_use_with_tool_result() -> None:
    p0 = _predicted(answer="100")
    assert to_messages([_turn("Q0", "tool_0", p0)], "Q1") == [
        _user_text("Q0"),
        _assistant_tool_use("tool_0", p0.model_dump()),
        _user_tool_result_then_text("tool_0", "Q1"),
    ]


def test_to_messages_three_prior_turns_full_alternation() -> None:
    p0, p1, p2 = _predicted("a"), _predicted("b"), _predicted("c")
    turns = [
        _turn("Q0", "tool_0", p0),
        _turn("Q1", "tool_1", p1),
        _turn("Q2", "tool_2", p2),
    ]
    assert to_messages(turns, "Q3") == [
        _user_text("Q0"),
        _assistant_tool_use("tool_0", p0.model_dump()),
        _user_tool_result_then_text("tool_0", "Q1"),
        _assistant_tool_use("tool_1", p1.model_dump()),
        _user_tool_result_then_text("tool_1", "Q2"),
        _assistant_tool_use("tool_2", p2.model_dump()),
        _user_tool_result_then_text("tool_2", "Q3"),
    ]


def test_to_messages_tool_use_id_matches_tool_result_id() -> None:
    msgs = to_messages([_turn("Q0", "abcd1234", _predicted())], "Q1")
    tool_use_id = msgs[1]["content"][0]["id"]
    tool_result_id = msgs[2]["content"][0]["tool_use_id"]
    assert tool_use_id == tool_result_id == "abcd1234"


# ---------- extract_tool_call --------------------------------------------


def _raw_with_tool_use(tool_input: dict) -> dict:
    return {
        "content": [
            {
                "type": "tool_use",
                "id": "tu_1",
                "name": TOOL_NAME,
                "input": tool_input,
            }
        ]
    }


def test_extract_tool_call_pulls_name_and_input() -> None:
    raw = _raw_with_tool_use({"answer": "yes"})
    assert extract_tool_call(raw) == {"name": TOOL_NAME, "input": {"answer": "yes"}}


def test_extract_tool_call_returns_none_when_absent() -> None:
    assert extract_tool_call({"content": [{"type": "text", "text": "x"}]}) is None


# ---------- render_messages_md -------------------------------------------


def test_render_messages_md_handles_string_user_and_block_lists() -> None:
    msgs = [
        _user_text("Q0"),
        _assistant_tool_use("tu_0", {"answer": "10", "calculation": "10"}),
        _user_tool_result_then_text("tu_0", "Q1"),
    ]
    rendered = render_messages_md(msgs)
    # String content stays a single line; blocks render with their type and id.
    assert "**[user]** Q0" in rendered
    assert "**[assistant tool_use tu_0]**" in rendered
    assert "answer=`10`" in rendered
    assert "**[user tool_result tu_0]** recorded" in rendered
    assert "**[user text]** Q1" in rendered
