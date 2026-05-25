"""Multi-turn answer generation; wire format isolated in the anthropic module."""

import time
from typing import Any

from pydantic import BaseModel

from src.domain import Conversation, ConvFinQARecord, Document, PredictedAnswer, Turn
from src.prompts.system import build_system_prompt
from src.services import anthropic
from src.services.llm_client import LLMClient
from src.tools.submit_answer import SubmitAnswer


class AnswerCall(BaseModel):
    predicted: PredictedAnswer
    system_prompt: str
    messages: list[dict[str, Any]]
    raw_response: dict[str, Any]
    latency_ms: int
    tokens_in: int
    tokens_out: int


class AnswerService:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def answer_turn(
        self,
        document: Document,
        prior_turns: list[Turn],
        question: str,
    ) -> tuple[Turn, AnswerCall]:
        """One LLM call: replay `prior_turns` then ask `question`."""
        system = build_system_prompt(document)
        messages = anthropic.to_messages(prior_turns, question)

        t0 = time.perf_counter()
        result = self._llm.predict_with_tool(
            system=system,
            messages=messages,
            tool_model=SubmitAnswer,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        predicted = PredictedAnswer.model_validate(result.parsed.model_dump())

        turn = Turn(
            question=question,
            tool_use_id=result.tool_use_id,
            predicted=predicted,
            assistant_exchange=result.assistant_exchange,
        )
        call = AnswerCall(
            predicted=predicted,
            system_prompt=system,
            messages=messages,
            raw_response=result.raw_response,
            latency_ms=latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
        )
        return turn, call

    def answer_single(self, document: Document, question: str) -> AnswerCall:
        _, call = self.answer_turn(document, [], question)
        return call

    def answer_conversation(
        self, record: ConvFinQARecord
    ) -> tuple[Conversation, list[AnswerCall]]:
        """Walk every question in `record.dialogue`, replaying prior turns each call."""
        conv = Conversation()
        calls: list[AnswerCall] = []
        for question in record.dialogue.conv_questions:
            turn, call = self.answer_turn(record.doc, conv.turns, question)
            conv.turns.append(turn)
            calls.append(call)
        return conv, calls
