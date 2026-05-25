"""Wiring tests for `AnswerService`. Uses an in-file fake — no API key."""

from collections import deque
from typing import Any

from pydantic import BaseModel

from src.domain import ConvFinQARecord, Dialogue, Document, Features, PredictedAnswer
from src.services.answer_service import AnswerService
from src.services.llm_client import LLMCallResult
from src.tools.submit_answer import SubmitAnswer


class _FakeLLMClient:
    def __init__(self, canned: list[BaseModel]) -> None:
        self._queue: deque[BaseModel] = deque(canned)
        self.calls: list[dict[str, Any]] = []

    def predict_with_tool(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tool_model: type[BaseModel],
    ) -> LLMCallResult:
        if not self._queue:
            raise RuntimeError("FakeLLMClient: no more canned responses")
        parsed = self._queue.popleft()
        idx = len(self.calls)
        tool_use_id = f"tool_{idx}"
        self.calls.append(
            {"system": system, "messages": messages, "tool_model": tool_model}
        )
        # Simulate what the real agentic loop returns: an assistant_exchange
        # containing just the submit_answer block (no calculator calls in the fake).
        assistant_exchange = [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": "submit_answer",
                        "input": parsed.model_dump(),
                    }
                ],
            }
        ]
        raw_response = {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": "submit_answer",
                    "input": parsed.model_dump(),
                }
            ]
        }
        return LLMCallResult(
            parsed=parsed,
            tool_use_id=tool_use_id,
            raw_response=raw_response,
            tokens_in=0,
            tokens_out=0,
            assistant_exchange=assistant_exchange,
        )


def test_answer_single_passes_question_and_returns_predicted_answer() -> None:
    canned = SubmitAnswer(
        reasoning="206588 - 181001 = 25587",
        answer="25587.0",
        unit="raw",
    )
    fake = _FakeLLMClient(canned=[canned])
    service = AnswerService(llm=fake)

    doc = Document(
        pre_text="narrative before",
        post_text="narrative after",
        table={"2009": {"net cash": 206588.0}, "2008": {"net cash": 181001.0}},
    )
    question = "what is the change in net cash from 2008 to 2009?"

    result = service.answer_single(doc, question)

    assert result.predicted == PredictedAnswer(
        reasoning="206588 - 181001 = 25587",
        answer="25587.0",
        unit="raw",
    )
    assert result.messages == [{"role": "user", "content": question}]
    assert "narrative before" in result.system_prompt
    assert "206588" in result.system_prompt
    assert result.raw_response

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["tool_model"] is SubmitAnswer
    assert call["messages"] == [{"role": "user", "content": question}]


def _record(questions: list[str], golds: list[float]) -> ConvFinQARecord:
    return ConvFinQARecord(
        id="rec/1",
        doc=Document(pre_text="pre", post_text="post", table={"2009": {"x": 1.0}}),
        dialogue=Dialogue(
            conv_questions=questions,
            conv_answers=[str(g) for g in golds],
            turn_program=["x"] * len(questions),
            executed_answers=list(golds),
            qa_split=[False] * len(questions),
        ),
        features=Features(
            num_dialogue_turns=len(questions),
            has_type2_question=False,
            has_duplicate_columns=False,
            has_non_numeric_values=False,
        ),
    )


def _canned(answer: str) -> SubmitAnswer:
    return SubmitAnswer(reasoning="r", answer=answer, unit="raw")


def test_answer_conversation_replays_prior_turns() -> None:
    record = _record(["Q0", "Q1", "Q2"], [10.0, 20.0, 30.0])
    fake = _FakeLLMClient(canned=[_canned("10"), _canned("20"), _canned("30")])
    service = AnswerService(llm=fake)

    conv, calls = service.answer_conversation(record)

    assert len(calls) == 3
    assert len(fake.calls) == 3

    # Turn 0: just the opening question
    assert fake.calls[0]["messages"] == [{"role": "user", "content": "Q0"}]

    # Turn 1: Q0 + turn 0's full exchange + tool_result ack + Q1
    assert fake.calls[1]["messages"] == [
        {"role": "user", "content": "Q0"},
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "tool_0",
                    "name": "submit_answer",
                    "input": _canned("10").model_dump(),
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "tool_0", "content": "recorded"},
                {"type": "text", "text": "Q1"},
            ],
        },
    ]

    assert [t.tool_use_id for t in conv.turns] == ["tool_0", "tool_1", "tool_2"]
    assert [t.predicted.answer for t in conv.turns] == ["10", "20", "30"]
    assert [t.question for t in conv.turns] == ["Q0", "Q1", "Q2"]
