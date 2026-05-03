"""Wiring test for `Answerer.answer_single`. Uses an in-file fake — no API key."""

from collections import deque
from typing import Any

from pydantic import BaseModel

from src.domain import Document, PredictedAnswer
from src.services.answerer import Answerer
from src.tools.submit_answer import SubmitAnswer


class _FakeLLMClient:
    """Pops one canned response per call. Records every call for assertions."""

    def __init__(self, canned: list[BaseModel]) -> None:
        self._queue: deque[BaseModel] = deque(canned)
        self.calls: list[dict[str, Any]] = []

    def predict_with_tool(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tool_model: type[BaseModel],
    ) -> tuple[BaseModel, dict[str, Any]]:
        if not self._queue:
            raise RuntimeError("FakeLLMClient: no more canned responses")
        parsed = self._queue.popleft()
        self.calls.append({"system": system, "messages": messages, "tool_model": tool_model})
        return parsed, {"content": [{"type": "tool_use", "input": parsed.model_dump()}]}


def test_answer_single_passes_question_and_returns_predicted_answer() -> None:
    canned = SubmitAnswer(
        reasoning="206588 - 181001 = 25587",
        calculation="206588 - 181001",
        answer="25587",
        unit="raw",
    )
    fake = _FakeLLMClient(canned=[canned])
    answerer = Answerer(llm=fake)

    doc = Document(
        pre_text="narrative before",
        post_text="narrative after",
        table={"2009": {"net cash": 206588.0}, "2008": {"net cash": 181001.0}},
    )
    question = "what is the change in net cash from 2008 to 2009?"

    result = answerer.answer_single(doc, question)

    assert result.predicted == PredictedAnswer(
        reasoning="206588 - 181001 = 25587",
        calculation="206588 - 181001",
        answer="25587",
        unit="raw",
    )
    # The trace carries everything needed for transcript replay.
    assert result.messages == [{"role": "user", "content": question}]
    assert "narrative before" in result.system_prompt
    assert "206588" in result.system_prompt
    assert result.raw_response  # populated by the fake

    # Wiring: exactly one call to the underlying LLM client.
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["tool_model"] is SubmitAnswer
    assert call["messages"] == [{"role": "user", "content": question}]
