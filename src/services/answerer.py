"""Multi-turn answerer.

`answer_single` handles a one-shot question (used for `peek` / smoke debug);
`answer_conversation` walks a record's full dialogue, replaying prior turns
each call so the model sees the alternating user/assistant/user history.

Wire-format concerns (message serialization, response decoding) live in
`anthropic`. This module is provider-agnostic above that seam.
"""

import time
from typing import Any

from pydantic import BaseModel

from src.domain import Conversation, ConvFinQARecord, Document, PredictedAnswer, Turn
from src.prompts.system import build_system_prompt
from src.services import anthropic
from src.services.llm_client import LLMClient
from src.tools.submit_answer import SubmitAnswer


class AnswerCall(BaseModel):
    """One LLM call: parsed answer + everything needed to replay or audit it.

    `latency_ms` is the wall time of the single `predict_with_tool` round-trip
    that produced this call. `tokens_in` / `tokens_out` are pulled from the
    provider's `usage` block. Both are per-call so late-turn cost (longer
    replayed history) is visible in metrics, not averaged into a flat number.
    """

    predicted: PredictedAnswer
    system_prompt: str
    messages: list[dict[str, Any]]
    raw_response: dict[str, Any]
    latency_ms: int
    tokens_in: int
    tokens_out: int


class Answerer:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def answer_single(self, document: Document, question: str) -> AnswerCall:
        system = build_system_prompt(document)
        messages: list[dict[str, Any]] = [{"role": "user", "content": question}]

        t0 = time.perf_counter()
        parsed, raw = self._llm.predict_with_tool(
            system=system,
            messages=messages,
            tool_model=SubmitAnswer,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        predicted = PredictedAnswer.model_validate(parsed.model_dump())
        result = anthropic.parse_response(raw)

        return AnswerCall(
            predicted=predicted,
            system_prompt=system,
            messages=messages,
            raw_response=raw,
            latency_ms=latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
        )

    def answer_conversation(
        self, record: ConvFinQARecord
    ) -> tuple[Conversation, list[AnswerCall]]:
        """Walk every question in `record.dialogue`, replaying prior turns.

        Returns the populated `Conversation` plus a list of `AnswerCall`s
        (one per turn, ordered) so the caller can score and write transcripts.
        """
        system = build_system_prompt(record.doc)
        conv = Conversation()
        calls: list[AnswerCall] = []

        for question in record.dialogue.conv_questions:
            messages = anthropic.to_messages(conv.turns, question)
            t0 = time.perf_counter()
            parsed, raw = self._llm.predict_with_tool(
                system=system,
                messages=messages,
                tool_model=SubmitAnswer,
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            predicted = PredictedAnswer.model_validate(parsed.model_dump())
            result = anthropic.parse_response(raw)

            calls.append(
                AnswerCall(
                    predicted=predicted,
                    system_prompt=system,
                    messages=messages,
                    raw_response=raw,
                    latency_ms=latency_ms,
                    tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out,
                )
            )
            conv.turns.append(
                Turn(
                    question=question,
                    tool_use_id=result.tool_use_id,
                    predicted=predicted,
                )
            )

        return conv, calls
